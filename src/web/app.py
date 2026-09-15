"""Web API REST e Servidor da Aplicação Clima Países utilizando FastAPI.

Responsabilidade:
- Expor endpoints REST documentados via Swagger OpenAPI (/docs).
- Servir a interface web estática (Dashboard SPA).
- Prover rotas de meteorologia, histórico de 10 anos, qualidade do ar e radar de precipitação.
- Executar operações de domínio em funções síncronas convencionais (def),
  permitindo ao FastAPI fazer o offload automático no threadpool sem travar o event loop.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

import requests
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.alerts import build_alerts
from src.api.historical import HistoricalWeatherClient
from src.api.open_meteo import OpenMeteoClient
from src.api.rest_countries import RestCountriesClient
from src.comparator import compare_cities
from src.match import CityMatcher
from src.resolver import resolve_place
from src.storage import StorageManager

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"
INDEX_HTML = STATIC_DIR / "index.html"
RAINVIEWER_MAPS_URL = "https://api.rainviewer.com/public/weather-maps.json"

app = FastAPI(
    title="Clima Países API",
    description="API REST para dados meteorológicos, previsões estendidas, histórico de 10 anos e radar de capitais mundiais.",
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS conforme spec: wildcard de origens só é válido sem credenciais
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicialização dos serviços de domínio
countries_client = RestCountriesClient()
countries = countries_client.load_countries()
matcher = CityMatcher(countries)
meteo_client = OpenMeteoClient()
hist_client = HistoricalWeatherClient()
storage = StorageManager()

# Monta diretório estático
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _resolve_coordinates(capital: str, country_cca2: str, country_latlng: list[float]) -> tuple[float, float, str]:
    """Obtém coordenadas precisas para uma capital."""
    coords = meteo_client.get_coordinates(capital, country_cca2)
    if coords:
        return coords[0], coords[1], coords[3]
    elif country_latlng and len(country_latlng) >= 2:
        return float(country_latlng[0]), float(country_latlng[1]), "auto"
    return 0.0, 0.0, "auto"


@app.get("/health", tags=["Sistema"])
def health_check() -> dict[str, str]:
    """Verifica a saúde do serviço."""
    return {"status": "healthy"}


@app.get("/", tags=["Interface Web"])
def read_root():
    """Serve o dashboard web SPA."""
    if INDEX_HTML.exists():
        return FileResponse(INDEX_HTML)
    return {"message": "Clima Países API ativa. Visite /docs para ver a documentação."}


@app.get("/api/weather/{query}", tags=["Meteorologia"])
def get_weather(query: str) -> dict[str, Any]:
    """Consulta o clima atual de uma capital, país ou código ISO."""
    match_res = resolve_place(query, matcher, meteo_client)
    if not match_res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capital ou país não encontrada para '{query}'.",
        )

    capital = match_res.capital
    country = match_res.country
    lat, lon, tz = _resolve_coordinates(capital, country.cca2, country.latlng)

    weather = meteo_client.get_current_weather(lat, lon, timezone=tz)
    if not weather:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Serviço meteorológico indisponível para {capital}.",
        )

    # Registra no histórico
    storage.add_history_entry(query, match_res, weather)

    return {
        "query": query,
        "capital": capital,
        "country": asdict(country),
        "weather": asdict(weather),
        "match": {
            "type": match_res.match_type,
            "confidence": match_res.confidence,
        },
    }


@app.get("/api/forecast/{query}", tags=["Meteorologia"])
def get_forecast(query: str, days: int = Query(default=5, ge=1, le=7)) -> dict[str, Any]:
    """Consulta a previsão estendida (clima atual, 5 dias, 24 horas e qualidade do ar)."""
    match_res = resolve_place(query, matcher, meteo_client)
    if not match_res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capital ou país não encontrada para '{query}'.",
        )

    capital = match_res.capital
    country = match_res.country
    lat, lon, tz = _resolve_coordinates(capital, country.cca2, country.latlng)

    extended = meteo_client.get_extended_forecast(lat, lon, timezone=tz, forecast_days=days, include_air_quality=True)
    if not extended:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Não foi possível obter a previsão estendida para {capital}.",
        )

    # Registra histórico
    storage.add_history_entry(query, match_res, extended.current)

    return {
        "query": query,
        "capital": capital,
        "country": asdict(country),
        "current": asdict(extended.current),
        "daily": [asdict(d) for d in extended.daily],
        "hourly": [asdict(h) for h in extended.hourly],
        "air_quality": asdict(extended.air_quality) if extended.air_quality else None,
        "alerts": [asdict(a) for a in build_alerts(extended)],
    }


@app.get("/api/historical/{query}", tags=["Análise Histórica"])
def get_historical(query: str, years: int = Query(default=10, ge=1, le=20)) -> dict[str, Any]:
    """Consulta análise histórica e anomalia climática dos últimos 10 a 20 anos na mesma data."""
    match_res = matcher.match(query)
    if not match_res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capital ou país não encontrada para '{query}'.",
        )

    capital = match_res.capital
    country = match_res.country
    lat, lon, tz = _resolve_coordinates(capital, country.cca2, country.latlng)

    weather = meteo_client.get_current_weather(lat, lon, timezone=tz)
    if not weather:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Não foi possível obter a temperatura atual para {capital}.",
        )

    analysis = hist_client.get_historical_analysis(
        capital=capital,
        country_name=country.name_pt,
        latitude=lat,
        longitude=lon,
        current_temp=weather.temperature,
        years_back=years,
        timezone=tz,
    )
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Registros históricos indisponíveis para {capital}.",
        )

    return asdict(analysis)


@app.get("/api/radar/layers", tags=["Radar Meteorológico"])
def get_radar_layers() -> dict[str, Any]:
    """Retorna os metadados e timestamps das camadas públicas de radar de precipitação (RainViewer API)."""
    try:
        resp = requests.get(RAINVIEWER_MAPS_URL, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço de radar meteorológico temporariamente indisponível.",
        )
    except requests.RequestException as e:
        logger.warning(f"Erro ao consultar RainViewer API: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível conectar ao serviço de radar.",
        )


@app.get("/api/air-quality/{query}", tags=["Qualidade do Ar"])
def get_air_quality(query: str) -> dict[str, Any]:
    """Consulta os dados de qualidade do ar (AQI, PM2.5, PM10, NO2, O3) para uma capital."""
    match_res = resolve_place(query, matcher, meteo_client)
    if not match_res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capital ou país não encontrada para '{query}'.",
        )

    capital = match_res.capital
    country = match_res.country
    lat, lon, _ = _resolve_coordinates(capital, country.cca2, country.latlng)

    air_quality = meteo_client.get_air_quality(lat, lon)
    if not air_quality:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Dados de qualidade do ar indisponíveis para {capital}.",
        )

    return {
        "capital": capital,
        "country": country.name_pt,
        "cca2": country.cca2,
        "air_quality": asdict(air_quality),
    }


@app.get("/api/compare", tags=["Comparação"])
def compare(cities: str = Query(..., description="Nomes das cidades separados por vírgula (ex: 'Brasilia,Tokyo,London')")) -> dict[str, Any]:
    """Compara o clima entre duas ou mais capitais simultaneamente."""
    city_list = [c.strip() for c in cities.split(",") if c.strip()]
    if len(city_list) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe ao menos 2 cidades separadas por vírgula para comparar.",
        )

    comparison = compare_cities(city_list, matcher, meteo_client)
    if not comparison.items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma das cidades informadas pôde ser encontrada.",
        )

    return comparison.to_summary_dict()


@app.get("/api/favorites", tags=["Favoritos"])
def get_favorites() -> list[dict[str, Any]]:
    """Retorna a lista de capitais favoritas salvas."""
    return storage.get_favorites()


@app.post("/api/favorites/{query}", tags=["Favoritos"])
def toggle_favorite(query: str) -> dict[str, Any]:
    """Adiciona ou remove uma capital dos favoritos."""
    match_res = resolve_place(query, matcher, meteo_client)
    if not match_res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capital '{query}' não encontrada.",
        )

    is_fav = storage.toggle_favorite(
        capital=match_res.capital,
        cca2=match_res.country.cca2,
        country_name=match_res.country.name_pt,
        flag=match_res.country.flag_emoji,
    )
    return {
        "capital": match_res.capital,
        "cca2": match_res.country.cca2,
        "is_favorite": is_fav,
        "message": f"{match_res.capital} {'adicionada aos' if is_fav else 'removida dos'} favoritos.",
    }


@app.get("/api/history", tags=["Histórico"])
def get_history(limit: int = Query(default=15, ge=1, le=50)) -> list[dict[str, Any]]:
    """Retorna o histórico recente de consultas."""
    return storage.get_history(limit=limit)

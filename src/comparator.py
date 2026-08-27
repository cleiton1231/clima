"""Módulo para análise comparativa de clima entre múltiplas capitais/cidades.

Responsabilidade:
- Cruzar dados meteorológicos simultâneos de duas ou mais cidades.
- Calcular métricas de diferença térmica (delta de temperatura), extremos (mais quente/fria),
  maior umidade e risco de chuva.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.api.open_meteo import OpenMeteoClient, WeatherData
    from src.match import CityMatcher, MatchResult


@dataclass
class CityComparisonItem:
    """Item individual de comparação com dados de matching e meteorologia."""

    query: str
    match_result: MatchResult
    weather: WeatherData


@dataclass
class ComparisonResult:
    """Resultado agregado de uma comparação multi-cidades."""

    items: list[CityComparisonItem]
    warmest: CityComparisonItem | None
    coldest: CityComparisonItem | None
    highest_humidity: CityComparisonItem | None
    highest_rain_risk: CityComparisonItem | None
    temp_delta: float  # Diferença entre a cidade mais quente e a mais fria em °C

    def to_summary_dict(self) -> dict:
        """Gera dicionário sumarizado para exportação ou exibição."""
        return {
            "cities_compared": [
                {
                    "capital": item.match_result.capital,
                    "country": item.match_result.country.name_pt,
                    "cca2": item.match_result.country.cca2,
                    "temperature": item.weather.temperature,
                    "apparent_temperature": item.weather.apparent_temperature,
                    "condition": item.weather.weather_description,
                    "humidity": item.weather.relative_humidity,
                    "wind_speed": item.weather.wind_speed,
                    "precipitation": item.weather.precipitation,
                }
                for item in self.items
            ],
            "warmest": self.warmest.match_result.capital if self.warmest else None,
            "coldest": self.coldest.match_result.capital if self.coldest else None,
            "temp_delta": round(self.temp_delta, 1),
        }


def compare_cities(
    queries: list[str], matcher: CityMatcher, meteo_client: OpenMeteoClient
) -> ComparisonResult:
    """Compara o clima de uma lista de cidades/capitais."""
    items: list[CityComparisonItem] = []

    for q in queries:
        q_clean = q.strip()
        if not q_clean:
            continue

        match_res = matcher.match(q_clean)
        if not match_res:
            continue

        capital = match_res.capital
        country = match_res.country

        coords = meteo_client.get_coordinates(capital, country.cca2)
        if coords:
            lat, lon, _, tz = coords
        elif country.latlng and len(country.latlng) >= 2:
            lat, lon = float(country.latlng[0]), float(country.latlng[1])
            tz = "auto"
        else:
            lat, lon, tz = 0.0, 0.0, "auto"

        weather = meteo_client.get_current_weather(lat, lon, timezone=tz)
        if weather:
            items.append(
                CityComparisonItem(
                    query=q_clean,
                    match_result=match_res,
                    weather=weather,
                )
            )

    if not items:
        return ComparisonResult(
            items=[],
            warmest=None,
            coldest=None,
            highest_humidity=None,
            highest_rain_risk=None,
            temp_delta=0.0,
        )

    # Ordena por temperatura decrescente
    sorted_by_temp = sorted(items, key=lambda x: x.weather.temperature, reverse=True)
    sorted_by_humidity = sorted(items, key=lambda x: x.weather.relative_humidity, reverse=True)
    sorted_by_precip = sorted(items, key=lambda x: x.weather.precipitation, reverse=True)

    warmest = sorted_by_temp[0]
    coldest = sorted_by_temp[-1]
    temp_delta = warmest.weather.temperature - coldest.weather.temperature

    return ComparisonResult(
        items=items,
        warmest=warmest,
        coldest=coldest,
        highest_humidity=sorted_by_humidity[0],
        highest_rain_risk=sorted_by_precip[0] if sorted_by_precip[0].weather.precipitation > 0 else None,
        temp_delta=round(temp_delta, 1),
    )

"""Cliente e integração com a API do Open-Meteo.

Responsabilidade:
- Consultar dados meteorológicos e clima atual utilizando coordenadas geográficas (latitude e longitude).
- Geocodificação de cidades/capitais para obter coordenadas precisas.
- Sem necessidade de chave de API ou token (Open-Meteo é livre e pública).
- Timeout explícito e tratamento robusto de erros HTTP/rede.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import requests

logger = logging.getLogger(__name__)

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

# Tabela de interpretação de código meteorológico WMO (WMO Weather interpretation codes)
WMO_WEATHER_CODES: dict[int, tuple[str, str, str]] = {
    # code: (descrição, emoji_dia, emoji_noite)
    0: ("Céu limpo", "☀️", "🌙"),
    1: ("Predominantemente limpo", "🌤️", "🌤️"),
    2: ("Parcialmente nublado", "⛅", "☁️"),
    3: ("Encoberto / Nublado", "☁️", "☁️"),
    45: ("Nevoeiro", "🌫️", "🌫️"),
    48: ("Nevoeiro com depósito de geada", "🌫️", "🌫️"),
    51: ("Chuvisco leve", "🌦️", "🌧️"),
    53: ("Chuvisco moderado", "🌦️", "🌧️"),
    55: ("Chuvisco denso", "🌧️", "🌧️"),
    56: ("Chuvisco congelante leve", "🌧️", "🌧️"),
    57: ("Chuvisco congelante denso", "🌧️", "🌧️"),
    61: ("Chuva fraca", "🌧️", "🌧️"),
    63: ("Chuva moderada", "🌧️", "🌧️"),
    65: ("Chuva forte", "🌧️", "🌧️"),
    66: ("Chuva congelante leve", "🌧️", "🌧️"),
    67: ("Chuva congelante forte", "🌧️", "🌧️"),
    71: ("Queda de neve leve", "🌨️", "🌨️"),
    73: ("Queda de neve moderada", "❄️", "❄️"),
    75: ("Queda de neve forte", "❄️", "❄️"),
    77: ("Grãos de neve", "❄️", "❄️"),
    80: ("Pancadas de chuva fracas", "🌦️", "🌧️"),
    81: ("Pancadas de chuva moderadas", "🌧️", "🌧️"),
    82: ("Pancadas de chuva violentas", "⛈️", "⛈️"),
    85: ("Pancadas de neve fracas", "🌨️", "🌨️"),
    86: ("Pancadas de neve fortes", "❄️", "❄️"),
    95: ("Tempestade / Trovoada", "⛈️", "⛈️"),
    96: ("Tempestade com granizo leve", "⛈️", "⛈️"),
    99: ("Tempestade com granizo forte", "⛈️", "⛈️"),
}


def interpret_weather_code(code: int, is_day: bool = True) -> tuple[str, str]:
    """Retorna a descrição em português e o emoji apropriado para o código WMO."""
    if code in WMO_WEATHER_CODES:
        desc, emoji_day, emoji_night = WMO_WEATHER_CODES[code]
        return desc, (emoji_day if is_day else emoji_night)
    return "Desconhecido", "🌡️"


@dataclass
class WeatherData:
    """Dados climáticos atuais estruturados."""

    temperature: float
    apparent_temperature: float
    relative_humidity: int
    wind_speed: float
    precipitation: float
    weather_code: int
    weather_description: str
    weather_emoji: str
    is_day: bool
    time: str
    latitude: float
    longitude: float
    elevation: float
    timezone: str


class OpenMeteoClient:
    """Cliente HTTP para comunicação com a API Open-Meteo."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def get_coordinates(
        self, city: str, country_code: str | None = None
    ) -> tuple[float, float, str, str] | None:
        """Busca as coordenadas geográficas precisas de uma cidade via Geocoding API.
        
        Retorna (latitude, longitude, nome_resolvido, timezone) ou None se não encontrado/erro.
        """
        if not city:
            return None

        params: dict[str, Any] = {
            "name": city,
            "count": 5,
            "language": "pt",
            "format": "json",
        }
        if country_code and len(country_code) == 2:
            params["country_code"] = country_code.upper()

        try:
            response = requests.get(
                OPEN_METEO_GEOCODING_URL,
                params=params,
                timeout=self.timeout,
            )
            if response.status_code == 200:
                data = response.json()
                results = data.get("results")
                if results and isinstance(results, list) and len(results) > 0:
                    best = results[0]
                    lat = float(best.get("latitude", 0.0))
                    lon = float(best.get("longitude", 0.0))
                    name = str(best.get("name", city))
                    tz = str(best.get("timezone", "UTC"))
                    return lat, lon, name, tz
            else:
                logger.warning(
                    f"Geocoding retornou status HTTP {response.status_code} para '{city}'"
                )
        except requests.RequestException as e:
            logger.warning(f"Erro ao buscar coordenadas para '{city}': {e}")

        return None

    def get_current_weather(
        self, latitude: float, longitude: float, timezone: str = "auto"
    ) -> WeatherData | None:
        """Obtém o clima atual para coordenadas de latitude e longitude."""
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": [
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "is_day",
                "precipitation",
                "weather_code",
                "wind_speed_10m",
            ],
            "timezone": timezone,
        }

        try:
            response = requests.get(
                OPEN_METEO_FORECAST_URL,
                params=params,
                timeout=self.timeout,
            )
            if response.status_code != 200:
                logger.warning(
                    f"Open-Meteo retornou status HTTP {response.status_code} para coords ({latitude}, {longitude})"
                )
                return None

            data = response.json()
            current = data.get("current", {})
            if not current:
                return None

            is_day = bool(current.get("is_day", 1))
            code = int(current.get("weather_code", 0))
            desc, emoji = interpret_weather_code(code, is_day=is_day)

            return WeatherData(
                temperature=float(current.get("temperature_2m", 0.0)),
                apparent_temperature=float(current.get("apparent_temperature", 0.0)),
                relative_humidity=int(current.get("relative_humidity_2m", 0)),
                wind_speed=float(current.get("wind_speed_10m", 0.0)),
                precipitation=float(current.get("precipitation", 0.0)),
                weather_code=code,
                weather_description=desc,
                weather_emoji=emoji,
                is_day=is_day,
                time=str(current.get("time", "")),
                latitude=float(data.get("latitude", latitude)),
                longitude=float(data.get("longitude", longitude)),
                elevation=float(data.get("elevation", 0.0)),
                timezone=str(data.get("timezone", timezone)),
            )
        except requests.RequestException as e:
            logger.warning(f"Erro ao consultar Open-Meteo: {e}")
            return None

"""Cliente e integração com a API do Open-Meteo.

Responsabilidade:
- Consultar dados meteorológicos em tempo real (clima atual).
- Consultar previsão diária estendida (até 5-7 dias) e horária (24 horas).
- Consultar dados de qualidade do ar (European AQI, PM2.5, PM10, NO2, O3).
- Geocodificação de cidades/capitais para obter coordenadas precisas.
- Sem necessidade de chave de API ou token (Open-Meteo é livre e pública).
- Timeout explícito e tratamento robusto de erros HTTP/rede.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import requests

logger = logging.getLogger(__name__)

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

# Tabela de interpretação de código meteorológico WMO
WMO_WEATHER_CODES: dict[int, tuple[str, str, str]] = {
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


def interpret_air_quality(aqi: int) -> tuple[str, str]:
    """Retorna a classificação e emoji para o Índice Europeu de Qualidade do Ar (AQI)."""
    if aqi <= 20:
        return "Excelente", "🟢"
    elif aqi <= 40:
        return "Bom", "🟢"
    elif aqi <= 60:
        return "Moderado", "🟡"
    elif aqi <= 80:
        return "Ruim", "🟠"
    elif aqi <= 100:
        return "Muito Ruim", "🔴"
    else:
        return "Extremamente Ruim", "🟣"


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


@dataclass
class DailyForecast:
    """Previsão diária resumida."""

    date: str
    weather_code: int
    weather_description: str
    weather_emoji: str
    temp_min: float
    temp_max: float
    precipitation_sum: float
    precipitation_probability_max: int
    uv_index_max: float
    sunrise: str
    sunset: str


@dataclass
class HourlyForecast:
    """Previsão horária estruturada."""

    time: str
    temperature: float
    precipitation_probability: int
    weather_code: int
    weather_description: str
    weather_emoji: str


@dataclass
class AirQualityData:
    """Dados de qualidade do ar estruturados."""

    european_aqi: int
    aqi_level: str
    aqi_emoji: str
    pm2_5: float
    pm10: float
    nitrogen_dioxide: float
    ozone: float


@dataclass
class ExtendedWeatherData:
    """Agregado com clima atual, previsão estendida e qualidade do ar."""

    current: WeatherData
    daily: list[DailyForecast] = field(default_factory=list)
    hourly: list[HourlyForecast] = field(default_factory=list)
    air_quality: AirQualityData | None = None


class OpenMeteoClient:
    """Cliente HTTP para comunicação com as APIs Open-Meteo."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def get_coordinates(
        self, city: str, country_code: str | None = None
    ) -> tuple[float, float, str, str] | None:
        """Busca as coordenadas geográficas precisas de uma cidade via Geocoding API."""
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
                    f"Open-Meteo retornou status HTTP {response.status_code} para ({latitude}, {longitude})"
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

    def get_air_quality(self, latitude: float, longitude: float) -> AirQualityData | None:
        """Obtém dados atuais de qualidade do ar via Open-Meteo Air Quality API."""
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": ["european_aqi", "pm2_5", "pm10", "nitrogen_dioxide", "ozone"],
        }
        try:
            response = requests.get(
                OPEN_METEO_AIR_QUALITY_URL,
                params=params,
                timeout=self.timeout,
            )
            if response.status_code == 200:
                data = response.json()
                curr = data.get("current", {})
                if curr:
                    aqi = int(curr.get("european_aqi") or 0)
                    level, emoji = interpret_air_quality(aqi)
                    return AirQualityData(
                        european_aqi=aqi,
                        aqi_level=level,
                        aqi_emoji=emoji,
                        pm2_5=float(curr.get("pm2_5") or 0.0),
                        pm10=float(curr.get("pm10") or 0.0),
                        nitrogen_dioxide=float(curr.get("nitrogen_dioxide") or 0.0),
                        ozone=float(curr.get("ozone") or 0.0),
                    )
        except requests.RequestException as e:
            logger.warning(f"Erro ao consultar qualidade do ar: {e}")
        return None

    def get_extended_forecast(
        self,
        latitude: float,
        longitude: float,
        timezone: str = "auto",
        forecast_days: int = 5,
        include_air_quality: bool = True,
    ) -> ExtendedWeatherData | None:
        """Obtém clima atual, previsão diária (próximos dias), horária (24h) e qualidade do ar."""
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
            "hourly": [
                "temperature_2m",
                "precipitation_probability",
                "weather_code",
            ],
            "daily": [
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "precipitation_probability_max",
                "uv_index_max",
                "sunrise",
                "sunset",
            ],
            "timezone": timezone,
            "forecast_days": forecast_days,
        }

        try:
            response = requests.get(
                OPEN_METEO_FORECAST_URL,
                params=params,
                timeout=self.timeout,
            )
            if response.status_code != 200:
                logger.warning(f"Erro HTTP {response.status_code} na previsão estendida")
                return None

            data = response.json()
            current_raw = data.get("current", {})
            if not current_raw:
                return None

            is_day = bool(current_raw.get("is_day", 1))
            code = int(current_raw.get("weather_code", 0))
            desc, emoji = interpret_weather_code(code, is_day=is_day)

            current_weather = WeatherData(
                temperature=float(current_raw.get("temperature_2m", 0.0)),
                apparent_temperature=float(current_raw.get("apparent_temperature", 0.0)),
                relative_humidity=int(current_raw.get("relative_humidity_2m", 0)),
                wind_speed=float(current_raw.get("wind_speed_10m", 0.0)),
                precipitation=float(current_raw.get("precipitation", 0.0)),
                weather_code=code,
                weather_description=desc,
                weather_emoji=emoji,
                is_day=is_day,
                time=str(current_raw.get("time", "")),
                latitude=float(data.get("latitude", latitude)),
                longitude=float(data.get("longitude", longitude)),
                elevation=float(data.get("elevation", 0.0)),
                timezone=str(data.get("timezone", timezone)),
            )

            # Processa Previsão Diária
            daily_list: list[DailyForecast] = []
            daily_raw = data.get("daily", {})
            times = daily_raw.get("time", [])
            w_codes = daily_raw.get("weather_code", [])
            t_maxs = daily_raw.get("temperature_2m_max", [])
            t_mins = daily_raw.get("temperature_2m_min", [])
            precip_sums = daily_raw.get("precipitation_sum", [])
            precip_probs = daily_raw.get("precipitation_probability_max", [])
            uv_maxs = daily_raw.get("uv_index_max", [])
            sunrises = daily_raw.get("sunrise", [])
            sunsets = daily_raw.get("sunset", [])

            for i in range(len(times)):
                d_code = int(w_codes[i]) if i < len(w_codes) else 0
                d_desc, d_emoji = interpret_weather_code(d_code, is_day=True)
                daily_list.append(
                    DailyForecast(
                        date=times[i],
                        weather_code=d_code,
                        weather_description=d_desc,
                        weather_emoji=d_emoji,
                        temp_min=float(t_mins[i]) if i < len(t_mins) else 0.0,
                        temp_max=float(t_maxs[i]) if i < len(t_maxs) else 0.0,
                        precipitation_sum=float(precip_sums[i]) if i < len(precip_sums) else 0.0,
                        precipitation_probability_max=int(precip_probs[i]) if i < len(precip_probs) and precip_probs[i] is not None else 0,
                        uv_index_max=float(uv_maxs[i]) if i < len(uv_maxs) and uv_maxs[i] is not None else 0.0,
                        sunrise=str(sunrises[i]) if i < len(sunrises) else "",
                        sunset=str(sunsets[i]) if i < len(sunsets) else "",
                    )
                )

            # Processa Previsão Horária (próximas 24 horas a partir do horário atual)
            hourly_list: list[HourlyForecast] = []
            hourly_raw = data.get("hourly", {})
            h_times = hourly_raw.get("time", [])
            h_temps = hourly_raw.get("temperature_2m", [])
            h_probs = hourly_raw.get("precipitation_probability", [])
            h_codes = hourly_raw.get("weather_code", [])

            # Limita às próximas 24 horas
            for i in range(min(24, len(h_times))):
                h_code = int(h_codes[i]) if i < len(h_codes) else 0
                # Extrai a hora se for dia/noite aproximado
                h_time_str = h_times[i]
                hour = int(h_time_str.split("T")[-1].split(":")[0]) if "T" in h_time_str else 12
                h_is_day = 6 <= hour <= 18
                h_desc, h_emoji = interpret_weather_code(h_code, is_day=h_is_day)
                hourly_list.append(
                    HourlyForecast(
                        time=h_time_str,
                        temperature=float(h_temps[i]) if i < len(h_temps) else 0.0,
                        precipitation_probability=int(h_probs[i]) if i < len(h_probs) and h_probs[i] is not None else 0,
                        weather_code=h_code,
                        weather_description=h_desc,
                        weather_emoji=h_emoji,
                    )
                )

            # Qualidade do ar (opcional)
            air_qual: AirQualityData | None = None
            if include_air_quality:
                air_qual = self.get_air_quality(latitude, longitude)

            return ExtendedWeatherData(
                current=current_weather,
                daily=daily_list,
                hourly=hourly_list,
                air_quality=air_qual,
            )

        except requests.RequestException as e:
            logger.warning(f"Erro de rede ao buscar previsão estendida: {e}")
            return None

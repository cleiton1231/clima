"""Regras de alertas climáticos derivados de previsão estendida e qualidade do ar.

Responsabilidade:
- Derivar alertas (tempestade, chuva intensa, UV, calor/frio extremo, ar ruim)
  exclusivamente dos dados já presentes em ExtendedWeatherData.
- Módulo puro: sem HTTP e sem dependência de renderização.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.api.open_meteo import ExtendedWeatherData


@dataclass
class Alert:
    """Alerta climático para exibição no CLI e na Web API."""

    level: str  # 'critico' | 'alto' | 'atencao'
    emoji: str
    title: str
    detail: str


def build_alerts(extended: "ExtendedWeatherData") -> list[Alert]:
    """Deriva alertas a partir dos dados já presentes em ExtendedWeatherData."""
    alerts: list[Alert] = []
    daily = extended.daily
    current = extended.current

    storm_days = [d.date for d in daily if d.weather_code >= 95]
    if current.weather_code >= 95:
        storm_days.append(current.time.split("T")[0])
    if storm_days:
        alerts.append(
            Alert(
                level="critico",
                emoji="⛈️",
                title="⛈️ Tempestade prevista",
                detail=", ".join(sorted(set(storm_days))),
            )
        )

    rain_days = [
        d.date
        for d in daily
        if d.precipitation_sum >= 10.0 or d.precipitation_probability_max >= 80
    ]
    if rain_days:
        alerts.append(
            Alert(
                level="alto",
                emoji="🌧️",
                title="🌧️ Risco alto de chuva",
                detail=", ".join(rain_days),
            )
        )

    uv_days = [d.date for d in daily if d.uv_index_max >= 8.0]
    if uv_days:
        alerts.append(
            Alert(
                level="atencao",
                emoji="☀️",
                title="☀️ Índice UV muito alto",
                detail=", ".join(uv_days),
            )
        )

    heat_days = [d.date for d in daily if d.temp_max >= 35.0]
    if heat_days or current.apparent_temperature >= 35.0:
        alerts.append(
            Alert(
                level="alto",
                emoji="🔥",
                title="🔥 Calor extremo",
                detail=", ".join(heat_days) if heat_days else "agora",
            )
        )

    cold_days = [d.date for d in daily if d.temp_min <= 0.0]
    if cold_days:
        alerts.append(
            Alert(
                level="atencao",
                emoji="❄️",
                title="❄️ Temperatura negativa",
                detail=", ".join(cold_days),
            )
        )

    if extended.air_quality and extended.air_quality.european_aqi > 80:
        alerts.append(
            Alert(
                level="alto",
                emoji="🌫️",
                title="🌫️ Qualidade do ar ruim",
                detail=f"AQI {extended.air_quality.european_aqi}",
            )
        )

    return alerts

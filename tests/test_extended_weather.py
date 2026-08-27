"""Testes para previsões diárias, horárias e qualidade do ar."""

from unittest.mock import MagicMock, patch
import pytest
from src.api.open_meteo import (
    OpenMeteoClient,
    DailyForecast,
    HourlyForecast,
    AirQualityData,
    ExtendedWeatherData,
    interpret_air_quality,
)


def test_interpret_air_quality():
    level_exc, emoji_exc = interpret_air_quality(15)
    assert level_exc == "Excelente"
    assert emoji_exc == "🟢"

    level_mod, emoji_mod = interpret_air_quality(50)
    assert level_mod == "Moderado"
    assert emoji_mod == "🟡"

    level_bad, emoji_bad = interpret_air_quality(85)
    assert level_bad == "Muito Ruim"
    assert emoji_bad == "🔴"

    level_ext, emoji_ext = interpret_air_quality(120)
    assert level_ext == "Extremamente Ruim"
    assert emoji_ext == "🟣"


@patch("requests.get")
def test_get_air_quality_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "current": {
            "european_aqi": 25,
            "pm2_5": 6.2,
            "pm10": 12.0,
            "nitrogen_dioxide": 5.1,
            "ozone": 80.4,
        }
    }
    mock_get.return_value = mock_resp

    client = OpenMeteoClient()
    aqi = client.get_air_quality(-15.78, -47.93)
    assert aqi is not None
    assert isinstance(aqi, AirQualityData)
    assert aqi.european_aqi == 25
    assert aqi.aqi_level == "Bom"
    assert aqi.pm2_5 == 6.2


@patch("requests.get")
def test_get_extended_forecast_success(mock_get):
    # Mock do retorno da API principal Open-Meteo
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "latitude": -15.78,
        "longitude": -47.93,
        "timezone": "America/Sao_Paulo",
        "elevation": 1170.0,
        "current": {
            "time": "2026-08-27T16:00",
            "temperature_2m": 29.0,
            "apparent_temperature": 28.5,
            "relative_humidity_2m": 35,
            "wind_speed_10m": 4.5,
            "precipitation": 0.0,
            "weather_code": 0,
            "is_day": 1,
        },
        "daily": {
            "time": ["2026-08-27", "2026-08-28", "2026-08-29"],
            "weather_code": [0, 2, 61],
            "temperature_2m_max": [30.0, 28.5, 26.0],
            "temperature_2m_min": [18.0, 17.5, 16.0],
            "precipitation_sum": [0.0, 0.2, 5.4],
            "precipitation_probability_max": [0, 20, 80],
            "uv_index_max": [8.5, 7.2, 5.0],
            "sunrise": ["2026-08-27T06:15", "2026-08-28T06:14", "2026-08-29T06:14"],
            "sunset": ["2026-08-27T18:05", "2026-08-28T18:05", "2026-08-29T18:05"],
        },
        "hourly": {
            "time": ["2026-08-27T00:00", "2026-08-27T01:00", "2026-08-27T02:00"],
            "temperature_2m": [20.0, 19.5, 19.0],
            "precipitation_probability": [0, 0, 5],
            "weather_code": [0, 0, 1],
        },
    }
    mock_get.return_value = mock_resp

    client = OpenMeteoClient()
    extended = client.get_extended_forecast(-15.78, -47.93, include_air_quality=False)
    assert extended is not None
    assert isinstance(extended, ExtendedWeatherData)
    assert extended.current.temperature == 29.0
    assert len(extended.daily) == 3
    assert extended.daily[0].temp_max == 30.0
    assert extended.daily[2].precipitation_probability_max == 80
    assert len(extended.hourly) == 3

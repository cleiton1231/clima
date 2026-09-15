"""Testes das regras de alertas climáticos."""

from src.alerts import build_alerts
from src.api.open_meteo import (
    AirQualityData,
    DailyForecast,
    ExtendedWeatherData,
    WeatherData,
)


def _extended(
    daily: list[DailyForecast] | None = None,
    air_quality: AirQualityData | None = None,
    current_temp: float = 22.0,
    current_code: int = 0,
) -> ExtendedWeatherData:
    weather = WeatherData(
        temperature=current_temp,
        apparent_temperature=current_temp,
        relative_humidity=50,
        wind_speed=5.0,
        precipitation=0.0,
        weather_code=current_code,
        weather_description="Céu limpo",
        weather_emoji="☀️",
        is_day=True,
        time="2026-08-27T16:00",
        latitude=0.0,
        longitude=0.0,
        elevation=0.0,
        timezone="UTC",
    )
    return ExtendedWeatherData(
        current=weather,
        daily=daily or [],
        hourly=[],
        air_quality=air_quality,
    )


def _day(
    code: int = 0,
    precip_sum: float = 0.0,
    precip_prob: int = 0,
    uv: float = 0.0,
    t_max: float = 25.0,
    t_min: float = 15.0,
    date: str = "2026-08-28",
) -> DailyForecast:
    return DailyForecast(
        date=date,
        weather_code=code,
        weather_description="x",
        weather_emoji="☀️",
        temp_min=t_min,
        temp_max=t_max,
        precipitation_sum=precip_sum,
        precipitation_probability_max=precip_prob,
        uv_index_max=uv,
        sunrise="06:00",
        sunset="18:00",
    )


def test_clima_limpo_gera_zero_alertas():
    assert build_alerts(_extended(daily=[_day()])) == []


def test_tempestade_alerta_critico():
    alerts = build_alerts(_extended(daily=[_day(code=95, date="2026-08-28")]))
    assert len(alerts) == 1
    assert alerts[0].level == "critico"
    assert "Tempestade" in alerts[0].title
    assert "2026-08-28" in alerts[0].detail


def test_chuva_intensa_por_mm_e_por_probabilidade():
    alerts_mm = build_alerts(_extended(daily=[_day(precip_sum=12.0)]))
    alerts_prob = build_alerts(_extended(daily=[_day(precip_prob=85)]))
    assert alerts_mm[0].title == "🌧️ Risco alto de chuva"
    assert alerts_prob[0].title == "🌧️ Risco alto de chuva"


def test_uv_muito_alto():
    alerts = build_alerts(_extended(daily=[_day(uv=8.5)]))
    assert len(alerts) == 1
    assert alerts[0].level == "atencao"
    assert "UV" in alerts[0].title


def test_calor_extremo_por_diario_e_por_sensacao():
    assert build_alerts(_extended(daily=[_day(t_max=36.0)]))[0].title == "🔥 Calor extremo"
    assert build_alerts(_extended(current_temp=35.5))[0].title == "🔥 Calor extremo"


def test_frio_extremo():
    alerts = build_alerts(_extended(daily=[_day(t_min=-2.0)]))
    assert alerts[0].title == "❄️ Temperatura negativa"


def test_qualidade_do_ar_ruim():
    aqi_ruim = AirQualityData(
        european_aqi=95,
        aqi_level="Muito Ruim",
        aqi_emoji="🔴",
        pm2_5=40.0,
        pm10=50.0,
        nitrogen_dioxide=5.0,
        ozone=80.0,
    )
    alerts = build_alerts(_extended(air_quality=aqi_ruim))
    assert alerts[0].title == "🌫️ Qualidade do ar ruim"
    assert alerts[0].level == "alto"

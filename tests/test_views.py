"""Testes unitários para renderização de views no terminal."""

from src.api.open_meteo import (
    AirQualityData,
    DailyForecast,
    ExtendedWeatherData,
    HourlyForecast,
    WeatherData,
)
from src.api.rest_countries import Country
from src.comparator import ComparisonResult, CityComparisonItem
from src.match import MatchResult
from src.ui.views import (
    render_24h_hourly,
    render_5day_forecast,
    render_air_quality,
    render_comparison_matrix,
    render_current_weather,
    render_extended_dashboard,
    render_favorites,
    render_history,
)


def test_views_render_without_errors():
    country = Country(
        name_common="France",
        name_official="French Republic",
        name_pt="França",
        capitals=["Paris"],
        cca2="FR",
        cca3="FRA",
        region="Europe",
        subregion="Western Europe",
        flag_emoji="🇫🇷",
    )
    match_res = MatchResult(
        capital="Paris",
        country=country,
        matched_term="paris",
        match_type="exact_capital",
        confidence=1.0,
    )
    weather = WeatherData(
        temperature=24.0,
        apparent_temperature=23.5,
        relative_humidity=55,
        wind_speed=8.0,
        precipitation=0.0,
        weather_code=0,
        weather_description="Céu limpo",
        weather_emoji="☀️",
        is_day=True,
        time="2026-08-27T16:00",
        latitude=48.85,
        longitude=2.35,
        elevation=35.0,
        timezone="Europe/Paris",
    )
    daily = [
        DailyForecast(
            date="2026-08-28",
            weather_code=0,
            weather_description="Céu limpo",
            weather_emoji="☀️",
            temp_min=15.0,
            temp_max=25.0,
            precipitation_sum=0.0,
            precipitation_probability_max=10,
            uv_index_max=5.5,
            sunrise="06:30",
            sunset="20:30",
        )
    ]
    hourly = [
        HourlyForecast(
            time="2026-08-28T00:00",
            temperature=18.0,
            precipitation_probability=0,
            weather_code=0,
            weather_description="Céu limpo",
            weather_emoji="☀️",
        )
    ]
    air = AirQualityData(
        european_aqi=28,
        aqi_level="Bom",
        aqi_emoji="🟢",
        pm2_5=8.0,
        pm10=14.0,
        nitrogen_dioxide=12.0,
        ozone=45.0,
    )
    extended = ExtendedWeatherData(
        current=weather,
        daily=daily,
        hourly=hourly,
        air_quality=air,
    )

    # Testa chamadas de renderização
    render_current_weather(match_res, weather)
    render_5day_forecast(daily)
    render_24h_hourly(hourly)
    render_air_quality(air)
    render_extended_dashboard(match_res, extended)

    # Comparação
    comp = ComparisonResult(
        items=[CityComparisonItem(query="Paris", match_result=match_res, weather=weather)],
        warmest=CityComparisonItem(query="Paris", match_result=match_res, weather=weather),
        coldest=CityComparisonItem(query="Paris", match_result=match_res, weather=weather),
        highest_humidity=CityComparisonItem(query="Paris", match_result=match_res, weather=weather),
        highest_rain_risk=None,
        temp_delta=0.0,
    )
    render_comparison_matrix(comp)

    # Favoritos e histórico
    render_favorites([{"capital": "Paris", "cca2": "FR", "country_name": "França", "flag": "🇫🇷", "added_at": "2026-08-27"}])
    render_favorites([])
    render_history([{"timestamp": "2026-08-27", "query": "Paris", "capital": "Paris", "country_name": "França", "temperature": 24.0, "emoji": "☀️", "condition": "Céu limpo"}])
    render_history([])


def test_render_historical_analysis_no_crash():
    from src.api.historical import HistoricalAnalysis
    from src.ui.views import render_historical_analysis

    analysis = HistoricalAnalysis(
        capital="Brasília",
        country_name="Brasil",
        target_date="2026-08-27",
        years_analyzed=10,
        current_temp=28.0,
        historical_mean_temp=23.5,
        historical_max_temp=31.0,
        historical_min_temp=17.0,
        temp_anomaly=4.5,
        anomaly_status="Muito acima da média histórica",
        anomaly_emoji="🔥",
        historical_avg_precip=0.2,
    )
    # Deve renderizar sem erro
    render_historical_analysis(analysis)


def test_render_alerts_imprime_e_ignora_vazio(capsys):
    from src.alerts import Alert
    from src.ui.views import render_alerts

    render_alerts([])  # vazio: no-op
    assert capsys.readouterr().out.strip() == ""

    alerts = [Alert(level="alto", emoji="🌧️", title="🌧️ Risco alto de chuva", detail="2026-08-28")]
    render_alerts(alerts)
    out = capsys.readouterr().out
    assert "⚠️" in out
    assert "Risco alto de chuva" in out

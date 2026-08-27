"""Testes para o módulo de comparação de capitais."""

from unittest.mock import MagicMock
import pytest
from src.api.open_meteo import WeatherData
from src.api.rest_countries import Country
from src.comparator import compare_cities, ComparisonResult
from src.match import MatchResult


def create_mock_city(capital, country_name, cca2, temp, humidity, precip):
    country = Country(
        name_common=country_name,
        name_official=country_name,
        name_pt=country_name,
        capitals=[capital],
        cca2=cca2,
        cca3=cca2 + "X",
        region="Test",
        subregion="Test",
        flag_emoji="🏳️",
    )
    match_res = MatchResult(
        capital=capital,
        country=country,
        matched_term=capital.lower(),
        match_type="exact_capital",
        confidence=1.0,
    )
    weather = WeatherData(
        temperature=temp,
        apparent_temperature=temp - 1.0,
        relative_humidity=humidity,
        wind_speed=10.0,
        precipitation=precip,
        weather_code=0,
        weather_description="Céu limpo",
        weather_emoji="☀️",
        is_day=True,
        time="2026-08-27T16:00",
        latitude=0.0,
        longitude=0.0,
        elevation=0.0,
        timezone="UTC",
    )
    return match_res, weather


def test_compare_cities_calculation():
    m1, w1 = create_mock_city("Brasília", "Brasil", "BR", 30.0, 40, 0.0)
    m2, w2 = create_mock_city("Oslo", "Noruega", "NO", 12.0, 75, 2.5)
    m3, w3 = create_mock_city("Tóquio", "Japão", "JP", 22.0, 60, 0.0)

    mock_matcher = MagicMock()
    mock_matcher.match.side_effect = lambda q: {
        "Brasília": m1,
        "Oslo": m2,
        "Tóquio": m3,
    }.get(q)

    mock_meteo = MagicMock()
    mock_meteo.get_coordinates.return_value = (0.0, 0.0, "Name", "UTC")
    mock_meteo.get_current_weather.side_effect = lambda lat, lon, timezone: {
        "BR": w1,
        "NO": w2,
        "JP": w3,
    }.get(timezone if timezone in ["BR", "NO", "JP"] else None, w1 if lat == 0.0 and mock_meteo.get_current_weather.call_count == 1 else (w2 if mock_meteo.get_current_weather.call_count == 2 else w3))

    res = compare_cities(["Brasília", "Oslo", "Tóquio"], mock_matcher, mock_meteo)
    assert isinstance(res, ComparisonResult)
    assert len(res.items) == 3
    assert res.warmest.match_result.capital == "Brasília"
    assert res.coldest.match_result.capital == "Oslo"
    assert res.temp_delta == 18.0
    assert res.highest_humidity.match_result.capital == "Oslo"
    assert res.highest_rain_risk.match_result.capital == "Oslo"

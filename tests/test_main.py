"""Testes para o fluxo da CLI principal."""

from unittest.mock import MagicMock
from src.main import search_and_display, format_weather_display
from src.api.open_meteo import WeatherData
from src.api.rest_countries import Country
from src.match import MatchResult


def test_search_and_display_success():
    country = Country(
        name_common="Brazil",
        name_official="Federative Republic of Brazil",
        name_pt="Brasil",
        capitals=["Brasília"],
        cca2="BR",
        cca3="BRA",
        region="Americas",
        subregion="South America",
        flag_emoji="🇧🇷",
        latlng=[-10, -55],
    )
    match_res = MatchResult(
        capital="Brasília",
        country=country,
        matched_term="brasilia",
        match_type="exact_capital",
        confidence=1.0,
    )
    mock_matcher = MagicMock()
    mock_matcher.match.return_value = match_res

    weather = WeatherData(
        temperature=25.0,
        apparent_temperature=24.5,
        relative_humidity=50,
        wind_speed=10.0,
        precipitation=0.0,
        weather_code=0,
        weather_description="Céu limpo",
        weather_emoji="☀️",
        is_day=True,
        time="2026-08-27T16:00",
        latitude=-15.78,
        longitude=-47.93,
        elevation=1172.0,
        timezone="America/Sao_Paulo",
    )
    mock_meteo = MagicMock()
    mock_meteo.get_coordinates.return_value = (-15.78, -47.93, "Brasília", "America/Sao_Paulo")
    mock_meteo.get_current_weather.return_value = weather

    assert search_and_display("Brasília", mock_matcher, mock_meteo) is True


def test_search_and_display_not_found():
    mock_matcher = MagicMock()
    mock_matcher.match.return_value = None
    mock_meteo = MagicMock()

    assert search_and_display("cidade_inexistente", mock_matcher, mock_meteo) is False


def test_search_and_display_empty_query():
    mock_matcher = MagicMock()
    mock_meteo = MagicMock()

    assert search_and_display("", mock_matcher, mock_meteo) is False

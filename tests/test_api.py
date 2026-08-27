"""Testes unitários para os clientes de API e conversão de dados."""

from unittest.mock import MagicMock, patch
import requests

from src.api.open_meteo import OpenMeteoClient, WeatherData, interpret_weather_code
from src.api.rest_countries import Country, RestCountriesClient, country_code_to_flag_emoji


class TestFlagEmoji:
    """Testes para conversão de código de país em emoji de bandeira."""

    def test_flag_emoji_conversion(self):
        assert country_code_to_flag_emoji("BR") == "🇧🇷"
        assert country_code_to_flag_emoji("US") == "🇺🇸"
        assert country_code_to_flag_emoji("JP") == "🇯🇵"
        assert country_code_to_flag_emoji("DE") == "🇩🇪"

    def test_flag_emoji_invalid(self):
        assert country_code_to_flag_emoji("") == "🌐"
        assert country_code_to_flag_emoji("INVALID") == "🌐"


class TestWeatherCodeInterpretation:
    """Testes para conversão de código WMO em descrição e emoji."""

    def test_clear_sky(self):
        desc, emoji_day = interpret_weather_code(0, is_day=True)
        assert desc == "Céu limpo"
        assert emoji_day == "☀️"

        _, emoji_night = interpret_weather_code(0, is_day=False)
        assert emoji_night == "🌙"

    def test_rain_and_thunderstorm(self):
        desc, emoji = interpret_weather_code(61, is_day=True)
        assert "Chuva" in desc
        assert emoji == "🌧️"

        desc_storm, emoji_storm = interpret_weather_code(95, is_day=True)
        assert "Tempestade" in desc_storm or "Trovoada" in desc_storm
        assert emoji_storm == "⛈️"

    def test_unknown_code(self):
        desc, emoji = interpret_weather_code(999, is_day=True)
        assert desc == "Desconhecido"
        assert emoji == "🌡️"


class TestOpenMeteoClient:
    """Testes para o cliente OpenMeteo com mocks de rede."""

    @patch("requests.get")
    def test_get_coordinates_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "name": "Brasília",
                    "latitude": -15.77972,
                    "longitude": -47.92972,
                    "timezone": "America/Sao_Paulo",
                }
            ]
        }
        mock_get.return_value = mock_response

        client = OpenMeteoClient()
        coords = client.get_coordinates("Brasília", "BR")
        assert coords is not None
        lat, lon, name, tz = coords
        assert lat == -15.77972
        assert lon == -47.92972
        assert name == "Brasília"
        assert tz == "America/Sao_Paulo"

    @patch("requests.get")
    def test_get_coordinates_network_error(self, mock_get):
        mock_get.side_effect = requests.RequestException("Timeout de rede")
        client = OpenMeteoClient()
        coords = client.get_coordinates("Brasília", "BR")
        assert coords is None

    @patch("requests.get")
    def test_get_current_weather_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "latitude": -15.78,
            "longitude": -47.93,
            "timezone": "America/Sao_Paulo",
            "elevation": 1172.0,
            "current": {
                "time": "2026-08-27T16:00",
                "temperature_2m": 27.5,
                "apparent_temperature": 26.8,
                "relative_humidity_2m": 42,
                "wind_speed_10m": 5.2,
                "precipitation": 0.0,
                "weather_code": 0,
                "is_day": 1,
            },
        }
        mock_get.return_value = mock_response

        client = OpenMeteoClient()
        weather = client.get_current_weather(-15.78, -47.93)
        assert weather is not None
        assert isinstance(weather, WeatherData)
        assert weather.temperature == 27.5
        assert weather.apparent_temperature == 26.8
        assert weather.relative_humidity == 42
        assert weather.weather_description == "Céu limpo"
        assert weather.weather_emoji == "☀️"

    @patch("requests.get")
    def test_get_current_weather_http_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        client = OpenMeteoClient()
        weather = client.get_current_weather(-15.78, -47.93)
        assert weather is None


class TestRestCountriesClient:
    """Testes para o cliente REST Countries."""

    def test_load_countries_from_local_cache(self):
        client = RestCountriesClient()
        countries = client.load_countries()
        assert len(countries) > 0
        br = client.get_by_cca2("BR")
        assert br is not None
        assert br.name_common == "Brazil"
        assert "Brasília" in br.capitals or "Brasilia" in br.capitals
        assert br.flag_emoji == "🇧🇷"

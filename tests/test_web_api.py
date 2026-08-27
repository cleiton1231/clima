"""Testes de integração da Web API FastAPI com isolamento de rede (mocks)."""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from src.api.open_meteo import (
    AirQualityData,
    DailyForecast,
    ExtendedWeatherData,
    HourlyForecast,
    WeatherData,
)
from src.api.rest_countries import Country
from src.match import MatchResult
from src.web.app import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_country_and_weather():
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
        latlng=[-10.0, -55.0],
    )
    match_res = MatchResult(
        capital="Brasília",
        country=country,
        matched_term="brasilia",
        match_type="exact_capital",
        confidence=1.0,
    )
    weather = WeatherData(
        temperature=28.0,
        apparent_temperature=27.5,
        relative_humidity=35,
        wind_speed=3.8,
        precipitation=0.0,
        weather_code=0,
        weather_description="Céu limpo",
        weather_emoji="☀️",
        is_day=True,
        time="2026-08-27T16:00",
        latitude=-15.78,
        longitude=-47.93,
        elevation=1170.0,
        timezone="America/Sao_Paulo",
    )
    daily = [
        DailyForecast(
            date="2026-08-28",
            weather_code=0,
            weather_description="Céu limpo",
            weather_emoji="☀️",
            temp_min=18.0,
            temp_max=31.0,
            precipitation_sum=0.0,
            precipitation_probability_max=0,
            uv_index_max=8.0,
            sunrise="06:20",
            sunset="18:05",
        )
    ]
    hourly = [
        HourlyForecast(
            time="2026-08-28T00:00",
            temperature=21.0,
            precipitation_probability=0,
            weather_code=0,
            weather_description="Céu limpo",
            weather_emoji="🌙",
        )
    ]
    air_quality = AirQualityData(
        european_aqi=45,
        aqi_level="Moderado",
        aqi_emoji="🟡",
        pm2_5=8.1,
        pm10=9.1,
        nitrogen_dioxide=1.7,
        ozone=110.0,
    )
    extended = ExtendedWeatherData(
        current=weather,
        daily=daily,
        hourly=hourly,
        air_quality=air_quality,
    )
    return match_res, weather, extended


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_root_index_html(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Clima Países" in response.text


def test_api_weather_success(client, mock_country_and_weather):
    match_res, weather, _ = mock_country_and_weather

    with patch("src.web.app.matcher.match", return_value=match_res), \
         patch("src.web.app.meteo_client.get_coordinates", return_value=(-15.78, -47.93, "Brasília", "America/Sao_Paulo")), \
         patch("src.web.app.meteo_client.get_current_weather", return_value=weather):

        response = client.get("/api/weather/Brasilia")
        assert response.status_code == 200
        data = response.json()
        assert data["capital"] == "Brasília"
        assert data["country"]["cca2"] == "BR"
        assert data["weather"]["temperature"] == 28.0
        assert data["weather"]["weather_emoji"] == "☀️"


def test_api_weather_not_found(client):
    with patch("src.web.app.matcher.match", return_value=None):
        response = client.get("/api/weather/cidade_que_nao_existe")
        assert response.status_code == 404
        assert "não encontrada" in response.json().get("detail", "").lower()


def test_api_forecast_success(client, mock_country_and_weather):
    match_res, _, extended = mock_country_and_weather

    with patch("src.web.app.matcher.match", return_value=match_res), \
         patch("src.web.app.meteo_client.get_coordinates", return_value=(-15.78, -47.93, "Brasília", "America/Sao_Paulo")), \
         patch("src.web.app.meteo_client.get_extended_forecast", return_value=extended):

        response = client.get("/api/forecast/Brasilia")
        assert response.status_code == 200
        data = response.json()
        assert data["capital"] == "Brasília"
        assert len(data["daily"]) == 1
        assert len(data["hourly"]) == 1
        assert data["daily"][0]["temp_max"] == 31.0


def test_api_air_quality_success(client, mock_country_and_weather):
    match_res, _, extended = mock_country_and_weather

    with patch("src.web.app.matcher.match", return_value=match_res), \
         patch("src.web.app.meteo_client.get_coordinates", return_value=(-15.78, -47.93, "Brasília", "America/Sao_Paulo")), \
         patch("src.web.app.meteo_client.get_air_quality", return_value=extended.air_quality):

        response = client.get("/api/air-quality/Brasilia")
        assert response.status_code == 200
        data = response.json()
        assert data["capital"] == "Brasília"
        assert data["air_quality"]["european_aqi"] == 45
        assert data["air_quality"]["aqi_level"] == "Moderado"


def test_api_compare_success(client, mock_country_and_weather):
    match_res, weather, _ = mock_country_and_weather

    with patch("src.web.app.matcher.match", return_value=match_res), \
         patch("src.web.app.meteo_client.get_coordinates", return_value=(-15.78, -47.93, "Brasília", "America/Sao_Paulo")), \
         patch("src.web.app.meteo_client.get_current_weather", return_value=weather):

        response = client.get("/api/compare?cities=Brasilia,Tokyo")
        assert response.status_code == 200
        data = response.json()
        assert "cities_compared" in data
        assert len(data["cities_compared"]) >= 1


def test_api_favorites_and_history(client, mock_country_and_weather):
    match_res, _, _ = mock_country_and_weather

    with patch("src.web.app.matcher.match", return_value=match_res):
        # Post favorite
        res_post = client.post("/api/favorites/Brasilia")
        assert res_post.status_code == 200
        assert "is_favorite" in res_post.json()

        # Get favorites
        res_get = client.get("/api/favorites")
        assert res_get.status_code == 200
        assert isinstance(res_get.json(), list)

        # Get history
        res_hist = client.get("/api/history")
        assert res_hist.status_code == 200
        assert isinstance(res_hist.json(), list)


def test_api_historical_success(client, mock_country_and_weather):
    match_res, weather, _ = mock_country_and_weather
    from src.api.historical import HistoricalAnalysis

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

    with patch("src.web.app.matcher.match", return_value=match_res), \
         patch("src.web.app.meteo_client.get_coordinates", return_value=(-15.78, -47.93, "Brasília", "America/Sao_Paulo")), \
         patch("src.web.app.meteo_client.get_current_weather", return_value=weather), \
         patch("src.web.app.hist_client.get_historical_analysis", return_value=analysis):

        response = client.get("/api/historical/Brasilia")
        assert response.status_code == 200
        data = response.json()
        assert data["capital"] == "Brasília"
        assert data["temp_anomaly"] == 4.5
        assert data["anomaly_emoji"] == "🔥"


def test_api_historical_not_found(client):
    with patch("src.web.app.matcher.match", return_value=None):
        response = client.get("/api/historical/cidade_inexistente")
        assert response.status_code == 404


def test_api_radar_layers_success(client):
    mock_rainviewer_data = {
        "version": "1.0",
        "generated": 1724774400,
        "host": "https://tilecache.rainviewer.com",
        "radar": {
            "past": [{"time": 1724773800, "path": "/v2/radar/1724773800/256/{z}/{x}/{y}/2/1_1.png"}],
            "nowcast": [{"time": 1724775000, "path": "/v2/radar/1724775000/256/{z}/{x}/{y}/2/1_1.png"}]
        }
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_rainviewer_data

    with patch("requests.get", return_value=mock_resp):
        response = client.get("/api/radar/layers")
        assert response.status_code == 200
        data = response.json()
        assert "host" in data
        assert "radar" in data
        assert len(data["radar"]["past"]) == 1

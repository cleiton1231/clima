"""Testes para o fluxo da CLI principal."""

from unittest.mock import MagicMock
from src.main import execute_city_query
from src.api.open_meteo import WeatherData, ExtendedWeatherData, DailyForecast, HourlyForecast, AirQualityData
from src.api.rest_countries import Country
from src.match import MatchResult
from src.storage import StorageManager


def test_execute_city_query_simple_weather(tmp_path):
    storage = StorageManager(tmp_path / "hist.json")
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

    assert execute_city_query("Brasília", mock_matcher, mock_meteo, storage) is True
    assert len(storage.get_history()) == 1


def test_execute_city_query_extended(tmp_path):
    storage = StorageManager(tmp_path / "hist.json")
    country = Country(
        name_common="Japan",
        name_official="Japan",
        name_pt="Japão",
        capitals=["Tokyo"],
        cca2="JP",
        cca3="JPN",
        region="Asia",
        subregion="Eastern Asia",
        flag_emoji="🇯🇵",
    )
    match_res = MatchResult(
        capital="Tokyo",
        country=country,
        matched_term="toquio",
        match_type="capital_alias",
        confidence=1.0,
    )
    mock_matcher = MagicMock()
    mock_matcher.match.return_value = match_res

    weather = WeatherData(
        temperature=22.0,
        apparent_temperature=21.5,
        relative_humidity=60,
        wind_speed=5.0,
        precipitation=0.0,
        weather_code=0,
        weather_description="Céu limpo",
        weather_emoji="☀️",
        is_day=True,
        time="2026-08-27T16:00",
        latitude=35.68,
        longitude=139.69,
        elevation=40.0,
        timezone="Asia/Tokyo",
    )
    extended = ExtendedWeatherData(
        current=weather,
        daily=[
            DailyForecast(
                date="2026-08-28",
                weather_code=0,
                weather_description="Céu limpo",
                weather_emoji="☀️",
                temp_min=18.0,
                temp_max=26.0,
                precipitation_sum=0.0,
                precipitation_probability_max=0,
                uv_index_max=6.0,
                sunrise="05:30",
                sunset="18:30",
            )
        ],
        hourly=[
            HourlyForecast(
                time="2026-08-28T00:00",
                temperature=20.0,
                precipitation_probability=0,
                weather_code=0,
                weather_description="Céu limpo",
                weather_emoji="☀️",
            )
        ],
        air_quality=AirQualityData(
            european_aqi=20,
            aqi_level="Excelente",
            aqi_emoji="🟢",
            pm2_5=5.0,
            pm10=10.0,
            nitrogen_dioxide=1.0,
            ozone=50.0,
        ),
    )
    mock_meteo = MagicMock()
    mock_meteo.get_coordinates.return_value = (35.68, 139.69, "Tokyo", "Asia/Tokyo")
    mock_meteo.get_extended_forecast.return_value = extended

    export_json_file = str(tmp_path / "tokyo.json")
    assert execute_city_query(
        "Tóquio",
        mock_matcher,
        mock_meteo,
        storage,
        show_all=True,
        export_format="json",
        export_output=export_json_file,
    ) is True


def test_execute_city_query_not_found(tmp_path):
    storage = StorageManager(tmp_path / "hist.json")
    mock_matcher = MagicMock()
    mock_matcher.match.return_value = None
    mock_meteo = MagicMock()

    assert execute_city_query("cidade_inexistente", mock_matcher, mock_meteo, storage) is False


def test_main_historical_flag(capsys):
    from unittest.mock import MagicMock, patch
    from src.main import main
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

    with patch("sys.argv", ["clima", "Brasília", "--historical"]), \
         patch("src.api.historical.HistoricalWeatherClient.get_historical_analysis", return_value=analysis):
        main()

    captured = capsys.readouterr()
    assert "Brasília" in captured.out or "Análise Histórica" in captured.out

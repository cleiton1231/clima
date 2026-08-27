"""Testes unitários para o módulo de análise histórica e anomalias climáticas."""

from unittest.mock import MagicMock, patch
import pytest
import requests

from src.api.historical import (
    HistoricalAnalysis,
    HistoricalWeatherClient,
    classify_temperature_anomaly,
)


def test_classify_temperature_anomaly():
    # Muito acima
    status, emoji = classify_temperature_anomaly(3.5)
    assert "Muito acima" in status
    assert emoji == "🔥"

    # Acima
    status, emoji = classify_temperature_anomaly(1.8)
    assert "Acima da média" in status
    assert emoji == "🔺"

    # Normal
    status, emoji = classify_temperature_anomaly(0.2)
    assert "normalidade" in status
    assert emoji == "🟢"

    # Abaixo
    status, emoji = classify_temperature_anomaly(-1.5)
    assert "Abaixo da média" in status
    assert emoji == "🔻"

    # Muito abaixo
    status, emoji = classify_temperature_anomaly(-4.0)
    assert "Muito abaixo" in status
    assert emoji == "❄️"


def test_historical_client_invalid_coordinates():
    client = HistoricalWeatherClient()
    with pytest.raises(ValueError, match="Latitude inválida"):
        client.get_historical_analysis("Brasília", "Brasil", 95.0, -47.93, current_temp=28.0)

    with pytest.raises(ValueError, match="Longitude inválida"):
        client.get_historical_analysis("Brasília", "Brasil", -15.78, 200.0, current_temp=28.0)


def test_historical_client_calculation_success():
    client = HistoricalWeatherClient()

    # Mock response da Open-Meteo Archive API
    mock_payload = {
        "daily": {
            "time": ["2016-08-27", "2017-08-27", "2018-08-27", "2019-08-27", "2020-08-27",
                     "2021-08-27", "2022-08-27", "2023-08-27", "2024-08-27", "2025-08-27"],
            "temperature_2m_mean": [22.0, 24.0, 23.0, 25.0, 22.5, 23.5, 24.5, 25.5, 23.0, 24.0],
            "temperature_2m_max": [28.0, 30.0, 29.0, 31.0, 28.5, 29.5, 30.5, 31.5, 29.0, 30.0],
            "temperature_2m_min": [16.0, 18.0, 17.0, 19.0, 16.5, 17.5, 18.5, 19.5, 17.0, 18.0],
            "precipitation_sum": [0.0, 0.5, 0.0, 1.2, 0.0, 0.0, 0.8, 0.0, 0.2, 0.0],
        }
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_payload

    with patch("requests.get", return_value=mock_resp) as mock_get:
        analysis = client.get_historical_analysis(
            capital="Brasília",
            country_name="Brasil",
            latitude=-15.78,
            longitude=-47.93,
            current_temp=28.0,
            target_date="2026-08-27",
            years_back=10,
        )

        assert mock_get.called
        assert analysis is not None
        assert analysis.capital == "Brasília"
        assert analysis.country_name == "Brasil"
        assert analysis.years_analyzed == 10
        assert analysis.current_temp == 28.0
        # Média das médias: 23.7 °C
        assert pytest.approx(analysis.historical_mean_temp, 0.1) == 23.7
        # Máxima histórica: 31.5 °C
        assert analysis.historical_max_temp == 31.5
        # Mínima histórica: 16.0 °C
        assert analysis.historical_min_temp == 16.0
        # Anomalia térmica: 28.0 - 23.7 = +4.3 °C (Muito acima)
        assert pytest.approx(analysis.temp_anomaly, 0.1) == 4.3
        assert "Muito acima" in analysis.anomaly_status
        assert analysis.anomaly_emoji == "🔥"


def test_historical_client_network_error():
    client = HistoricalWeatherClient()

    with patch("requests.get", side_effect=requests.RequestException("Timeout")):
        analysis = client.get_historical_analysis(
            capital="Brasília",
            country_name="Brasil",
            latitude=-15.78,
            longitude=-47.93,
            current_temp=28.0,
        )
        assert analysis is None

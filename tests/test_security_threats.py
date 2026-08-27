"""Testes de segurança e validação de ameaças (STRIDE & OWASP Top 10)."""

import pytest
from src.api.historical import HistoricalWeatherClient, OPEN_METEO_HISTORICAL_URL
from src.api.open_meteo import OPEN_METEO_GEOCODING_URL, OPEN_METEO_FORECAST_URL, OPEN_METEO_AIR_QUALITY_URL
from src.match import normalize_text


def test_security_coordinate_boundary_rejection():
    client = HistoricalWeatherClient()

    # Latitudes fora do intervalo [-90, 90]
    with pytest.raises(ValueError):
        client.get_historical_analysis("Teste", "País", 90.1, 0.0, 20.0)
    with pytest.raises(ValueError):
        client.get_historical_analysis("Teste", "País", -90.1, 0.0, 20.0)

    # Longitudes fora do intervalo [-180, 180]
    with pytest.raises(ValueError):
        client.get_historical_analysis("Teste", "País", 0.0, 180.1, 20.0)
    with pytest.raises(ValueError):
        client.get_historical_analysis("Teste", "País", 0.0, -180.1, 20.0)


def test_security_ssrf_hardcoded_domains():
    # Validação de que todas as URLs base são estritamente HTTPS oficiais
    assert OPEN_METEO_HISTORICAL_URL.startswith("https://archive-api.open-meteo.com")
    assert OPEN_METEO_FORECAST_URL.startswith("https://api.open-meteo.com")
    assert OPEN_METEO_GEOCODING_URL.startswith("https://geocoding-api.open-meteo.com")
    assert OPEN_METEO_AIR_QUALITY_URL.startswith("https://air-quality-api.open-meteo.com")


def test_security_query_sanitization_and_special_chars():
    # Teste de caracteres maliciosos e injeção de script
    malicious_query = "<script>alert('xss')</script>"
    clean = normalize_text(malicious_query)
    assert "<script>" not in clean
    assert "alert" in clean

    # Path traversal attempt
    traversal_query = "../../../etc/passwd"
    clean_traversal = normalize_text(traversal_query)
    assert "../" not in clean_traversal

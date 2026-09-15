"""Testes do resolver: matcher local com fallback de geocoding."""

from unittest.mock import MagicMock

from src.api.open_meteo import PlaceHit
from src.match import MatchResult
from src.resolver import resolve_place


def test_matcher_tem_prioridade_sobre_geocoding():
    match_res = MatchResult(
        capital="Paris",
        country=MagicMock(),
        matched_term="paris",
        match_type="exact_capital",
        confidence=1.0,
    )
    matcher = MagicMock()
    matcher.match.return_value = match_res
    meteo = MagicMock()

    result = resolve_place("Paris", matcher, meteo)

    assert result is match_res
    meteo.search_place.assert_not_called()


def test_fallback_geocoding_para_cidade_nao_capital():
    matcher = MagicMock()
    matcher.match.return_value = None
    meteo = MagicMock()
    meteo.search_place.return_value = PlaceHit(
        name="São Paulo",
        latitude=-23.5505,
        longitude=-46.6333,
        timezone="America/Sao_Paulo",
        country="Brazil",
        country_code="BR",
    )

    result = resolve_place("sao paulo", matcher, meteo)

    assert result is not None
    assert result.capital == "São Paulo"
    assert result.match_type == "geocoding_fallback"
    assert result.country.cca2 == "BR"
    assert result.country.flag_emoji == "🇧🇷"


def test_retorna_none_quando_ambos_falham():
    matcher = MagicMock()
    matcher.match.return_value = None
    meteo = MagicMock()
    meteo.search_place.return_value = None

    assert resolve_place("cidade inexistente", matcher, meteo) is None

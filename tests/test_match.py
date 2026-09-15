"""Testes unitários para o módulo de matching de cidades/capitais."""

import pytest
from src.api.rest_countries import RestCountriesClient
from src.match import CityMatcher, normalize_text


@pytest.fixture(scope="module")
def matcher():
    client = RestCountriesClient()
    countries = client.load_countries()
    assert len(countries) > 0, "Deveria carregar países do dataset"
    return CityMatcher(countries)


class TestTextNormalization:
    """Testes para a função normalize_text."""

    def test_accents_removal(self):
        assert normalize_text("Brasília") == "brasilia"
        assert normalize_text("Bogotá") == "bogota"
        assert normalize_text("São Tomé") == "sao tome"
        assert normalize_text("Reykjavík") == "reykjavik"
        assert normalize_text("Asunción") == "asuncion"

    def test_case_insensitivity(self):
        assert normalize_text("PARIS") == "paris"
        assert normalize_text("ToKyO") == "tokyo"

    def test_punctuation_handling(self):
        assert normalize_text("Washington, D.C.") == "washington d c"
        assert normalize_text("St. John's") == "st john s"

    def test_whitespace_trimming(self):
        assert normalize_text("  Madrid   ") == "madrid"
        assert normalize_text("Buenos    Aires") == "buenos aires"

    def test_empty_and_none(self):
        assert normalize_text("") == ""
        assert normalize_text(None) == ""


class TestCapitalMatching:
    """Testes para matching direto de capitais e variações de idioma."""

    @pytest.mark.parametrize(
        "query, expected_capital, expected_cca2",
        [
            ("Brasília", "Brasília", "BR"),
            ("brasilia", "Brasília", "BR"),
            ("BRASILIA", "Brasília", "BR"),
            ("Rome", "Rome", "IT"),
            ("roma", "Rome", "IT"),
            ("Vienna", "Vienna", "AT"),
            ("viena", "Vienna", "AT"),
            ("Lisbon", "Lisbon", "PT"),
            ("lisboa", "Lisbon", "PT"),
            ("London", "London", "GB"),
            ("londres", "London", "GB"),
            ("Tokyo", "Tokyo", "JP"),
            ("Tóquio", "Tokyo", "JP"),
            ("toquio", "Tokyo", "JP"),
            ("Beijing", "Beijing", "CN"),
            ("pequim", "Beijing", "CN"),
            ("Moscow", "Moscow", "RU"),
            ("moscou", "Moscow", "RU"),
            ("Athens", "Athens", "GR"),
            ("atenas", "Athens", "GR"),
            ("Warsaw", "Warsaw", "PL"),
            ("varsóvia", "Warsaw", "PL"),
            ("Prague", "Prague", "CZ"),
            ("praga", "Prague", "CZ"),
            ("Brussels", "Brussels", "BE"),
            ("bruxelas", "Brussels", "BE"),
            ("Copenhagen", "Copenhagen", "DK"),
            ("copenhague", "Copenhagen", "DK"),
            ("Kyiv", "Kyiv", "UA"),
            ("kiev", "Kyiv", "UA"),
            ("Berlin", "Berlin", "DE"),
            ("berlim", "Berlin", "DE"),
            ("Madrid", "Madrid", "ES"),
            ("madri", "Madrid", "ES"),
            ("Paris", "Paris", "FR"),
            ("Buenos Aires", "Buenos Aires", "AR"),
            ("Santiago", "Santiago", "CL"),
            ("Montevideo", "Montevideo", "UY"),
            ("montevideu", "Montevideo", "UY"),
            ("Bogotá", "Bogotá", "CO"),
            ("bogota", "Bogotá", "CO"),
            ("Lima", "Lima", "PE"),
            ("Quito", "Quito", "EC"),
            ("Caracas", "Caracas", "VE"),
            ("Havana", "Havana", "CU"),
            ("Ottawa", "Ottawa", "CA"),
            ("Canberra", "Canberra", "AU"),
            ("camberra", "Canberra", "AU"),
            ("Washington, D.C.", "Washington, D.C.", "US"),
            ("Washington DC", "Washington, D.C.", "US"),
            ("Washington", "Washington, D.C.", "US"),
        ],
    )
    def test_capital_resolution(self, matcher, query, expected_capital, expected_cca2):
        result = matcher.match(query)
        assert result is not None, f"Query '{query}' deveria ter sido resolvida"
        assert result.country.cca2 == expected_cca2
        assert normalize_text(result.capital) == normalize_text(expected_capital)
        assert result.confidence >= 0.8


class TestCountryToCapitalMatching:
    """Testes para resolução de nome ou código de país para sua capital."""

    @pytest.mark.parametrize(
        "country_query, expected_capital, expected_cca2",
        [
            ("Brasil", "Brasília", "BR"),
            ("Brazil", "Brasília", "BR"),
            ("Alemanha", "Berlin", "DE"),
            ("Germany", "Berlin", "DE"),
            ("Japão", "Tokyo", "JP"),
            ("Japan", "Tokyo", "JP"),
            ("França", "Paris", "FR"),
            ("France", "Paris", "FR"),
            ("Itália", "Rome", "IT"),
            ("Italy", "Rome", "IT"),
            ("Espanha", "Madrid", "ES"),
            ("Spain", "Madrid", "ES"),
            ("Portugal", "Lisbon", "PT"),
            ("Estados Unidos", "Washington, D.C.", "US"),
            ("USA", "Washington, D.C.", "US"),
            ("EUA", "Washington, D.C.", "US"),
            ("Reino Unido", "London", "GB"),
            ("UK", "London", "GB"),
            ("Canadá", "Ottawa", "CA"),
            ("Austrália", "Canberra", "AU"),
            ("Argentina", "Buenos Aires", "AR"),
            ("Chile", "Santiago", "CL"),
            ("Uruguai", "Montevideo", "UY"),
        ],
    )
    def test_country_name_resolution(self, matcher, country_query, expected_capital, expected_cca2):
        result = matcher.match(country_query)
        assert result is not None, f"País '{country_query}' deveria resolver para sua capital"
        assert result.country.cca2 == expected_cca2
        assert normalize_text(result.capital) == normalize_text(expected_capital)


class TestISOCodeMatching:
    """Testes para resolução por códigos ISO alpha-2 e alpha-3."""

    @pytest.mark.parametrize(
        "code, expected_cca2",
        [
            ("BR", "BR"),
            ("BRA", "BR"),
            ("US", "US"),
            ("DE", "DE"),
            ("DEU", "DE"),
            ("JP", "JP"),
            ("JPN", "JP"),
            ("FR", "FR"),
            ("FRA", "FR"),
            ("IT", "IT"),
            ("ITA", "IT"),
            ("PT", "PT"),
            ("PRT", "PT"),
        ],
    )
    def test_iso_code_resolution(self, matcher, code, expected_cca2):
        result = matcher.match(code)
        assert result is not None, f"Código '{code}' deveria ser resolvido"
        assert result.country.cca2 == expected_cca2


class TestFuzzyAndTypos:
    """Testes de tolerância a pequenos erros de digitação (fuzzy matching)."""

    @pytest.mark.parametrize(
        "typo_query, expected_cca2",
        [
            ("Baris", "FR"),       # Erro de 1 letra em Paris
            ("Berlimm", "DE"),     # Letra duplicada em Berlim
            ("Lisboaa", "PT"),     # Letra duplicada em Lisboa
            ("Tokyoo", "JP"),      # Letra duplicada em Tokyo
            ("Londress", "GB"),    # Letra duplicada em Londres
        ],
    )
    def test_typo_resolution(self, matcher, typo_query, expected_cca2):
        result = matcher.match(typo_query, min_confidence=0.70)
        assert result is not None, f"Typo '{typo_query}' deveria encontrar o match correto"
        assert result.country.cca2 == expected_cca2


class TestInvalidAndEdgeCases:
    """Testes para entradas inválidas, vazias ou não encontradas."""

    @pytest.mark.parametrize(
        "invalid_query",
        [
            "",
            "   ",
            "asdfghjklqwerty123456",
            "!@#$%¨&*",
            "cidade_que_nao_existe_123",
        ],
    )
    def test_invalid_queries_return_none_safely(self, matcher, invalid_query):
        result = matcher.match(invalid_query)
        assert result is None, f"Query '{invalid_query}' deveria retornar None sem exceção"


class TestMatchingAmbiguidades:
    """Casos de ambiguidade descobertos na simulação de 2026-09-15."""

    def test_cingapura_nao_deve_cair_em_prefixo_curto(self, matcher):
        # 'cin' (3 chars) não deve vencer por prefixo; fuzzy resolve Singapura
        res = matcher.match("Cingapura")
        assert res is not None
        assert res.country.cca2 == "SG"

    def test_salvador_resolve_cidade_brasileira(self, matcher):
        res = matcher.match("Salvador")
        assert res is not None
        assert res.capital == "Salvador"
        assert res.country.cca2 == "BR"

    def test_san_salvador_e_el_salvador_continuam_bolivia_deles(self, matcher):
        san = matcher.match("San Salvador")
        assert san is not None and san.country.cca2 == "SV"
        el = matcher.match("El Salvador")
        assert el is not None and el.country.cca2 == "SV"

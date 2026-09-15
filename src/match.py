"""Módulo de normalização e matching de cidades/capitais.

Responsabilidade:
- Resolver a correspondência entre a entrada do usuário e os dados da REST Countries.
- Lidar com acentuação, maiúsculas/minúsculas, abreviações, sinônimos, nomes locais vs. nomes em inglês/português.
- Fallback determinístico e testável (parte crítica do projeto).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from src.api.rest_countries import Country

try:
    from rapidfuzz import fuzz  # type: ignore
    HAS_RAPIDFUZZ = True
except ImportError:
    import difflib
    HAS_RAPIDFUZZ = False


def normalize_text(text: str) -> str:
    """Normaliza texto: remove acentos, pontuações, espaços extras e converte para minúsculas.
    
    Exemplos:
        'Brasília' -> 'brasilia'
        'Washington, D.C.' -> 'washington dc'
        'St. John's' -> 'st johns'
    """
    if not text:
        return ""
    
    # Decomposição Unicode para separar diacríticos
    decomposed = unicodedata.normalize("NFKD", text)
    # Remove marcas de diacríticos (acentos)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    
    # Converte para minúsculas
    lowered = without_accents.lower()
    
    # Substitui pontuações e caracteres especiais por espaços
    cleaned = re.sub(r"[^\w\s]", " ", lowered)
    
    # Remove múltiplos espaços consecutivos e espaços nas pontas
    return re.sub(r"\s+", " ", cleaned).strip()


# Dicionário de sinônimos/aliases comuns de capitais (multilíngue -> capital canônica)
CAPITAL_ALIASES: dict[str, tuple[str, str]] = {
    # 'alias_normalizado': ('Capital Canônica', 'Código CCA2 do País')
    "roma": ("Rome", "IT"),
    "rome": ("Rome", "IT"),
    "viena": ("Vienna", "AT"),
    "vienna": ("Vienna", "AT"),
    "lisboa": ("Lisbon", "PT"),
    "lisbon": ("Lisbon", "PT"),
    "londres": ("London", "GB"),
    "london": ("London", "GB"),
    "toquio": ("Tokyo", "JP"),
    "tokyo": ("Tokyo", "JP"),
    "pequim": ("Beijing", "CN"),
    "beijing": ("Beijing", "CN"),
    "moscou": ("Moscow", "RU"),
    "moscow": ("Moscow", "RU"),
    "atenas": ("Athens", "GR"),
    "athens": ("Athens", "GR"),
    "varsovia": ("Warsaw", "PL"),
    "warsaw": ("Warsaw", "PL"),
    "praga": ("Prague", "CZ"),
    "prague": ("Prague", "CZ"),
    "bruxelas": ("Brussels", "BE"),
    "brussels": ("Brussels", "BE"),
    "copenhague": ("Copenhagen", "DK"),
    "copenhaga": ("Copenhagen", "DK"),
    "copenhagen": ("Copenhagen", "DK"),
    "estocolmo": ("Stockholm", "SE"),
    "stockholm": ("Stockholm", "SE"),
    "bucareste": ("Bucharest", "RO"),
    "bucharest": ("Bucharest", "RO"),
    "belgrado": ("Belgrade", "RS"),
    "belgrade": ("Belgrade", "RS"),
    "kiev": ("Kyiv", "UA"),
    "kyiv": ("Kyiv", "UA"),
    "washington": ("Washington, D.C.", "US"),
    "washington dc": ("Washington, D.C.", "US"),
    "washington d c": ("Washington, D.C.", "US"),
    "washington distrito de columbia": ("Washington, D.C.", "US"),
    "cidade do mexico": ("Mexico City", "MX"),
    "ciudad de mexico": ("Mexico City", "MX"),
    "mexico city": ("Mexico City", "MX"),
    "cidade do cabo": ("Cape Town", "ZA"),
    "cape town": ("Cape Town", "ZA"),
    "pretoria": ("Pretoria", "ZA"),
    "nova delhi": ("New Delhi", "IN"),
    "nova deli": ("New Delhi", "IN"),
    "new delhi": ("New Delhi", "IN"),
    "camberra": ("Canberra", "AU"),
    "canberra": ("Canberra", "AU"),
    "ottawa": ("Ottawa", "CA"),
    "otava": ("Ottawa", "CA"),
    "santiago": ("Santiago", "CL"),
    "buenos aires": ("Buenos Aires", "AR"),
    "montevideu": ("Montevideo", "UY"),
    "montevideo": ("Montevideo", "UY"),
    "assuncao": ("Asunción", "PY"),
    "asuncion": ("Asunción", "PY"),
    "la paz": ("La Paz", "BO"),
    "sucre": ("Sucre", "BO"),
    "lima": ("Lima", "PE"),
    "bogota": ("Bogotá", "CO"),
    "caracas": ("Caracas", "VE"),
    "quito": ("Quito", "EC"),
    "havana": ("Havana", "CU"),
    "la habana": ("Havana", "CU"),
    "berlim": ("Berlin", "DE"),
    "berlin": ("Berlin", "DE"),
    "madri": ("Madrid", "ES"),
    "madrid": ("Madrid", "ES"),
    "helsinque": ("Helsinki", "FI"),
    "helsinki": ("Helsinki", "FI"),
    "oslo": ("Oslo", "NO"),
    "reikjavik": ("Reykjavik", "IS"),
    "reykjavik": ("Reykjavik", "IS"),
    "reiquiavique": ("Reykjavik", "IS"),
    "dublin": ("Dublin", "IE"),
    "amsterda": ("Amsterdam", "NL"),
    "amsterdam": ("Amsterdam", "NL"),
    "berna": ("Bern", "CH"),
    "bern": ("Bern", "CH"),
    "ancara": ("Ankara", "TR"),
    "ankara": ("Ankara", "TR"),
    "seul": ("Seoul", "KR"),
    "seoul": ("Seoul", "KR"),
    "pyongyang": ("Pyongyang", "KP"),
    "pionguiangue": ("Pyongyang", "KP"),
    "bangcoc": ("Bangkok", "TH"),
    "bangkok": ("Bangkok", "TH"),
    "jacarta": ("Jakarta", "ID"),
    "jakarta": ("Jakarta", "ID"),
    "manila": ("Manila", "PH"),
    "hanoi": ("Hanoi", "VN"),
    "singapura": ("Singapore", "SG"),
    "singapore": ("Singapore", "SG"),
    "cairo": ("Cairo", "EG"),
    "nairobi": ("Nairobi", "KE"),
    "rabat": ("Rabat", "MA"),
    "abu dhabi": ("Abu Dhabi", "AE"),
    "abudhabi": ("Abu Dhabi", "AE"),
    "riad": ("Riyadh", "SA"),
    "riyadh": ("Riyadh", "SA"),
    "doha": ("Doha", "QA"),
    "jerusalem": ("Jerusalem", "IL"),
    "teera": ("Tehran", "IR"),
    "tehran": ("Tehran", "IR"),
    "bagda": ("Baghdad", "IQ"),
    "baghdad": ("Baghdad", "IQ"),
    "beirute": ("Beirut", "LB"),
    "beirut": ("Beirut", "LB"),
    "damasco": ("Damascus", "SY"),
    "damascus": ("Damascus", "SY"),
    "luanda": ("Luanda", "AO"),
    "maputo": ("Maputo", "MZ"),
    "praia": ("Praia", "CV"),
    "bissau": ("Bissau", "GW"),
    "sao tome": ("São Tomé", "ST"),
    "dili": ("Dili", "TL"),
    # Cidades importantes que não são capitais (resolvidas via geocoding com o CCA2 do país)
    "salvador": ("Salvador", "BR"),
    "nova york": ("New York", "US"),
    "new york": ("New York", "US"),
    "manaus": ("Manaus", "BR"),
}

# Aliases comuns de nomes de países (multilíngue / abreviações -> Código CCA2)
COUNTRY_ALIASES: dict[str, str] = {
    "eua": "US",
    "usa": "US",
    "estados unidos": "US",
    "estados unidos da america": "US",
    "united states": "US",
    "united states of america": "US",
    "uk": "GB",
    "reino unido": "GB",
    "united kingdom": "GB",
    "gra bretanha": "GB",
    "great britain": "GB",
    "inglaterra": "GB",
    "england": "GB",
    "brasil": "BR",
    "brazil": "BR",
    "alemanha": "DE",
    "germany": "DE",
    "deutschland": "DE",
    "japao": "JP",
    "japan": "JP",
    "espanha": "ES",
    "spain": "ES",
    "espana": "ES",
    "franca": "FR",
    "france": "FR",
    "italia": "IT",
    "italy": "IT",
    "russia": "RU",
    "china": "CN",
    "coreia do sul": "KR",
    "south korea": "KR",
    "coreia do norte": "KP",
    "north korea": "KP",
    "emirados arabes": "AE",
    "emirados arabes unidos": "AE",
    "uae": "AE",
    "holanda": "NL",
    "netherlands": "NL",
    "paises baixos": "NL",
    "suica": "CH",
    "switzerland": "CH",
    "suécia": "SE",
    "suecia": "SE",
    "sweden": "SE",
    "africa do sul": "ZA",
    "south africa": "ZA",
}


@dataclass
class MatchResult:
    """Resultado estruturado de um matching de cidade/capital."""

    capital: str
    country: Country
    matched_term: str
    match_type: str  # 'exact_capital', 'capital_alias', 'country_name', 'country_code', 'fuzzy'
    confidence: float  # 0.0 a 1.0


class CityMatcher:
    """Mecanismo de resolução e matching difuso de cidades e capitais."""

    def __init__(self, countries: Iterable[Country]):
        self.countries = list(countries)
        self._countries_by_cca2: dict[str, Country] = {c.cca2: c for c in self.countries if c.cca2}
        self._countries_by_cca3: dict[str, Country] = {c.cca3: c for c in self.countries if c.cca3}
        
        # Índices normalizados para lookup direto
        self._capital_index: dict[str, tuple[str, Country]] = {}
        self._country_index: dict[str, Country] = {}
        self._all_searchable_terms: dict[str, tuple[str, Country, str]] = {}
        
        self._build_indices()

    def _build_indices(self) -> None:
        """Constrói os índices de busca a partir da lista de países."""
        for country in self.countries:
            # Indexa códigos ISO
            if country.cca2:
                norm_cca2 = normalize_text(country.cca2)
                self._country_index[norm_cca2] = country
            if country.cca3:
                norm_cca3 = normalize_text(country.cca3)
                self._country_index[norm_cca3] = country

            # Indexa nomes de países
            for name in [country.name_common, country.name_official, country.name_pt]:
                norm_name = normalize_text(name)
                if norm_name:
                    self._country_index[norm_name] = country
                    self._all_searchable_terms[norm_name] = (country.primary_capital, country, "country_name")

            # Indexa traduções de países
            for trans in country.translations.values():
                norm_trans = normalize_text(trans)
                if norm_trans:
                    self._country_index[norm_trans] = country
                    self._all_searchable_terms[norm_trans] = (country.primary_capital, country, "country_translation")

            # Indexa nomes nativos
            for native in country.native_names:
                norm_nat = normalize_text(native)
                if norm_nat:
                    self._country_index[norm_nat] = country

            # Indexa capitais do país
            for cap in country.capitals:
                norm_cap = normalize_text(cap)
                if norm_cap:
                    self._capital_index[norm_cap] = (cap, country)
                    self._all_searchable_terms[norm_cap] = (cap, country, "exact_capital")

        # Adiciona Aliases predefinidos de capitais
        for alias_norm, (canonical_cap, cca2) in CAPITAL_ALIASES.items():
            country = self._countries_by_cca2.get(cca2)
            if country:
                self._capital_index[alias_norm] = (canonical_cap, country)
                self._all_searchable_terms[alias_norm] = (canonical_cap, country, "capital_alias")

        # Adiciona Aliases predefinidos de países
        for alias_norm, cca2 in COUNTRY_ALIASES.items():
            country = self._countries_by_cca2.get(cca2)
            if country:
                self._country_index[alias_norm] = country
                self._all_searchable_terms[alias_norm] = (country.primary_capital, country, "country_alias")

    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """Calcula similaridade entre 0.0 e 1.0."""
        if not s1 or not s2:
            return 0.0
        if HAS_RAPIDFUZZ:
            return fuzz.ratio(s1, s2) / 100.0
        return difflib.SequenceMatcher(None, s1, s2).ratio()

    def match(self, query: str, min_confidence: float = 0.75) -> MatchResult | None:
        """Resolve uma query de entrada do usuário para uma capital e país.
        
        Ordem de resolução determinística:
        1. Correspondência exata normalizada em índice de capitais/aliases.
        2. Correspondência exata normalizada em código ISO de país (CCA2/CCA3).
        3. Correspondência exata normalizada em nome/tradução de país -> retorna capital principal.
        4. Correspondência de prefixo/substring.
        5. Matching difuso (fuzzy) com score acima do limiar min_confidence.
        """
        if not query or not query.strip():
            return None

        norm_query = normalize_text(query)
        if not norm_query:
            return None

        # 1. Match exato em índice de capitais
        if norm_query in self._capital_index:
            cap, country = self._capital_index[norm_query]
            return MatchResult(
                capital=cap,
                country=country,
                matched_term=norm_query,
                match_type="exact_capital",
                confidence=1.0,
            )

        # 2. Match exato em código ou nome de país
        if norm_query in self._country_index:
            country = self._country_index[norm_query]
            if country.capitals:
                return MatchResult(
                    capital=country.primary_capital,
                    country=country,
                    matched_term=norm_query,
                    match_type="country_exact",
                    confidence=1.0,
                )

        # 3. Match por prefixo/substring em capitais ou termos conhecidos
        for term, (cap, country, mtype) in self._all_searchable_terms.items():
            if not cap:
                continue
            # Prefixo exige tamanho mínimo em AMBOS os lados (evita termos curtos
            # indexados, como 'cin', sequestrando queries longas)
            if (
                len(norm_query) >= 4
                and len(term) >= 4
                and (term.startswith(norm_query) or norm_query.startswith(term))
            ):
                return MatchResult(
                    capital=cap,
                    country=country,
                    matched_term=term,
                    match_type="prefix_match",
                    confidence=0.90,
                )

        # 4. Fallback: Fuzzy matching em todos os termos indexados
        best_score = 0.0
        best_match: tuple[str, Country, str, str] | None = None

        for term, (cap, country, mtype) in self._all_searchable_terms.items():
            if not cap:
                continue
            score = self._calculate_similarity(norm_query, term)
            if score > best_score:
                best_score = score
                best_match = (cap, country, term, mtype)

        if best_match and best_score >= min_confidence:
            cap, country, term, mtype = best_match
            return MatchResult(
                capital=cap,
                country=country,
                matched_term=term,
                match_type=f"fuzzy_{mtype}",
                confidence=round(best_score, 3),
            )

        return None

"""Resolver de consultas: matcher local de capitais + fallback de geocoding Open-Meteo.

Responsabilidade:
- Priorizar o CityMatcher local (determinístico e testável).
- Fallback: consultar a Geocoding API Open-Meteo para cidades que não são capitais.
- Converter o resultado do geocoding em Country/MatchResult para reusar views e storage.
"""

from __future__ import annotations

from src.api.open_meteo import OpenMeteoClient, PlaceHit
from src.api.rest_countries import Country, country_code_to_flag_emoji
from src.match import CityMatcher, MatchResult


def _country_from_place(hit: PlaceHit) -> Country:
    cca2 = hit.country_code.upper()
    return Country(
        name_common=hit.country or hit.name,
        name_official=hit.country or hit.name,
        name_pt=hit.country or hit.name,
        capitals=[hit.name],
        cca2=cca2,
        cca3="",
        region="",
        subregion="",
        flag_emoji=country_code_to_flag_emoji(cca2),
        latlng=[hit.latitude, hit.longitude],
    )


def resolve_place(
    query: str, matcher: CityMatcher, meteo_client: OpenMeteoClient
) -> MatchResult | None:
    """Resolve a query pelo matcher de capitais; se falhar, usa o geocoding Open-Meteo."""
    if not query or not query.strip():
        return None

    match_res = matcher.match(query.strip())
    if match_res:
        return match_res

    hit = meteo_client.search_place(query.strip())
    if not hit or not hit.country_code:
        return None

    return MatchResult(
        capital=hit.name,
        country=_country_from_place(hit),
        matched_term=hit.name.lower(),
        match_type="geocoding_fallback",
        confidence=1.0,
    )

"""Region-to-country mappings for eligibility checks and geographic linking.

Single source of truth used by ``EligibilityFilterService`` and ``LinkingService``.
Macro-region keys (e.g. ``asia``) are normalized with :func:`entity_matches_region`.
"""

from __future__ import annotations

# Lowercase nationality / country strings grouped by broad region (heuristic MVP).
REGION_TO_COUNTRIES: dict[str, frozenset[str]] = {
    "asia": frozenset(
        {
            "bangladesh",
            "cambodia",
            "china",
            "india",
            "indonesia",
            "japan",
            "malaysia",
            "myanmar",
            "nepal",
            "pakistan",
            "philippines",
            "singapore",
            "south korea",
            "sri lanka",
            "taiwan",
            "thailand",
            "vietnam",
        }
    ),
    "europe": frozenset(
        {
            "austria",
            "belgium",
            "czech republic",
            "denmark",
            "finland",
            "france",
            "germany",
            "ireland",
            "italy",
            "netherlands",
            "norway",
            "poland",
            "portugal",
            "spain",
            "sweden",
            "switzerland",
            "uk",
            "united kingdom",
        }
    ),
    "north america": frozenset({"canada", "mexico", "usa", "united states"}),
    "south america": frozenset(
        {
            "argentina",
            "brazil",
            "chile",
            "colombia",
            "peru",
            "venezuela",
        }
    ),
    "oceania": frozenset({"australia", "new zealand"}),
    "africa": frozenset(
        {
            "egypt",
            "ethiopia",
            "ghana",
            "kenya",
            "nigeria",
            "south africa",
        }
    ),
}


def entity_matches_region(entity: str, region: str) -> bool:
    """Return True if *entity* (nationality or country string) satisfies *region* label.

    *region* may be a known macro-region key (for example ``asia``) or a literal
    country or nationality string for exact match.
    """
    entity_lower = entity.lower().strip()
    region_lower = region.lower().strip()

    countries = REGION_TO_COUNTRIES.get(region_lower)
    if countries is not None:
        return entity_lower in countries

    return entity_lower == region_lower

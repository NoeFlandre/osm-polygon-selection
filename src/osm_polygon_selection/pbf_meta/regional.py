"""Canonical regional sub-PBF map for large countries.

Single source of truth for: which Geofabrik PBF slugs are
sub-regions of a parent country. Used by:

- ``dataset_build.countries`` to skip sub-PBFs when scanning ``raw/``.
- ``country_notes`` to render the per-country README's "source
  description" line ("processed via N Geofabrik regional sub-PBFs").

Both consumers MUST derive from this module so the build skip-list
and the README regional list cannot drift.

A ``has_extra_keys`` test in tests/test_regional_metadata_in_sync.py
pins that any country listed here is also listed in both
``dataset_build.countries.REGIONAL_CHILDREN`` and
``country_notes.REGIONAL_SUB_PBFS``.

The map includes entries that are required by build behavior but
not shown in the public README (e.g. ``haute-normandie``,
``bermuda``, ``falklands``).
"""

from __future__ import annotations

__all__ = ["REGIONAL_SUB_PBFS_CANONICAL", "ALL_REGIONAL_CANONICAL"]


# Canonical map: parent -> set of child PBF slugs.
# This is a SUPERSET of what the public README shows. The build
# pipeline needs every regional sub-PBF to be filtered out, even
# ones we don't surface in the per-country README.
REGIONAL_SUB_PBFS_CANONICAL: dict[str, set[str]] = {
    "france": {
        "alsace", "aquitaine", "auvergne", "basse-normandie", "bourgogne",
        "bretagne", "centre", "champagne-ardenne", "corse", "franche-comte",
        "guadeloupe", "guyane", "haute-normandie", "ile-de-france",
        "languedoc-roussillon", "limousin", "lorraine", "martinique",
        "mayotte", "midi-pyrenees", "nord-pas-de-calais", "pays-de-la-loire",
        "picardie", "poitou-charentes", "provence-alpes-cote-d-azur",
        "reunion", "rhone-alpes",
    },
    "germany": {
        "baden-wuerttemberg", "bayern", "berlin", "brandenburg", "bremen",
        "hamburg", "hessen", "mecklenburg-vorpommern", "niedersachsen",
        "nordrhein-westfalen", "rheinland-pfalz", "saarland", "sachsen",
        "sachsen-anhalt", "schleswig-holstein", "thueringen",
    },
    "norway": {
        "nord-norge", "ostlandet", "sorlandet", "svalbard-janmayen",
        "trondelag", "vestlandet",
    },
    "italy": {
        "centro", "isole", "nord-est", "nord-ovest", "sud",
    },
    "netherlands": {
        "drenthe", "flevoland", "friesland", "gelderland", "groningen",
        "limburg", "noord-brabant", "noord-holland", "overijssel",
        "utrecht", "zeeland", "zuid-holland",
    },
    "poland": {
        "dolnoslaskie", "kujawsko-pomorskie", "lodzkie", "lubelskie",
        "lubuskie", "malopolskie", "mazowieckie", "opolskie",
        "podkarpackie", "podlaskie", "pomorskie", "slaskie",
        "swietokrzyskie", "warminsko-mazurskie", "wielkopolskie",
        "zachodniopomorskie",
    },
    "spain": {
        "andalucia", "aragon", "asturias", "cantabria",
        "castilla-la-mancha", "castilla-y-leon", "cataluna", "ceuta",
        "extremadura", "galicia", "islas-baleares", "la-rioja",
        "madrid", "melilla", "murcia", "navarra", "pais-vasco",
        "valencia",
    },
    "united-kingdom": {
        "england", "scotland", "wales", "bermuda", "falklands",
    },
}


# Flat set of every regional child slug, derived from the canonical map.
ALL_REGIONAL_CANONICAL: set[str] = {
    child for children in REGIONAL_SUB_PBFS_CANONICAL.values() for child in children
}

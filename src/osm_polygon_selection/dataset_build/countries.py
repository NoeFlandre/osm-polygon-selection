"""Regional sub-PBF metadata for large countries.

Some countries on Geofabrik are not provided as a single monolithic
PBF; instead the per-country page links out to a list of sub-PBFs
(administrative regions). When we walk ``raw/`` for these parents,
we must NOT treat each child as an independent country.

For example, ``france-latest.osm.pbf`` does not exist on Geofabrik,
but ``alsace-latest.osm.pbf``, ``bretagne-latest.osm.pbf``, etc.
do. The parent slug (``france``) is recorded as the country in our
manifest, and each child is silently merged under it.

This module owns the source-of-truth mapping parent -> set(children),
plus an ``ALL_REGIONAL`` flat set and an ``is_regional_child``
predicate for use in the dataset extraction pipeline.
"""

from __future__ import annotations

__all__ = ["REGIONAL_CHILDREN", "ALL_REGIONAL", "is_regional_child"]


REGIONAL_CHILDREN: dict[str, set[str]] = {
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

# Flat set of every regional child slug, pre-computed for the
# per-PBF hot path in main(). Used to skip sub-regional PBFs that
# belong under a parent we already cover.
ALL_REGIONAL: set[str] = {
    child for children in REGIONAL_CHILDREN.values() for child in children
}


def is_regional_child(country: str) -> bool:
    """Return True if ``country`` is a regional sub-PBF of some parent.

    Used by the dataset extraction pipeline to skip regional sub-PBFs
    when scanning ``raw/`` for independent country datasets.
    """
    return country in ALL_REGIONAL

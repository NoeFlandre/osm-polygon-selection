"""Per-country note helpers.

Pure formatting functions over COUNTRY_NOTES + REGIONAL_SUB_PBFS.
"""

from __future__ import annotations

from osm_polygon_selection.country_notes.data import (
    COUNTRY_NOTES,
    REGIONAL_SUB_PBFS,
)


def country_source_description(country: str) -> str:
    """One-line description of the source PBF(s) used for this country."""
    if country in REGIONAL_SUB_PBFS:
        n = len(REGIONAL_SUB_PBFS[country])
        return f"`{country}-latest.osm.pbf` *processed via {n} Geofabrik regional sub-PBFs*"
    return f"`{country}-latest.osm.pbf`"


def country_note(country: str, n_polygons: int, extract_status: str) -> str:
    """Return a 1-paragraph blurb for a country, falling back to a generic line."""
    if country in COUNTRY_NOTES:
        return COUNTRY_NOTES[country]
    from osm_polygon_selection.pbf_meta import geofabrik_url
    return (
        f"{country.title()} has {n_polygons:,} polygons in this dataset. "
        f"Extract status: **{extract_status}**. "
        f"Source: Geofabrik [`{country}-latest.osm.pbf`]({geofabrik_url(country)})."
    )


__all__ = ["country_note", "country_source_description"]

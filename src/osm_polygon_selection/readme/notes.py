"""Per-country README note adapter.

A thin shim around ``osm_polygon_selection.country_notes`` that
returns a 1-2 sentence note about a country, with a generic
fallback sized to the polygon count. Keeps the country README
renderer free of business logic about note selection.
"""

from __future__ import annotations

from osm_polygon_selection.country_notes import COUNTRY_NOTES


def country_note(country: str, n_polygons: int) -> str:
    """Return a 1-2 sentence note about this country, or generic fallback.

    Sources curated notes from ``osm_polygon_selection.country_notes``;
    falls back to a generic line sized to the polygon count.
    """
    note = COUNTRY_NOTES.get(country, "")
    if note:
        return note
    if n_polygons <= 100:
        return f"Tiny country with only {n_polygons:,} polygons surviving the size filter."
    if n_polygons <= 5000:
        return f"Small country with {n_polygons:,} polygons. Most urban + coastal features."
    return ""

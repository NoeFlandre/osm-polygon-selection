"""Per-country README rendering.

Produces the ``per_country/<country>/README.md`` content (one per
country). The template lives in ``readme.templates.COUNTRY_README_TEMPLATE``
so this module stays small (~30 LOC).
"""

from __future__ import annotations

from osm_polygon_selection.pbf_meta import geofabrik_url
from osm_polygon_selection.readme.notes import country_note
from osm_polygon_selection.readme.templates import COUNTRY_README_TEMPLATE


def build_country_readme(
    country: str,
    n_polygons: int,
    extract_status: str,
    pbf_date: str,
) -> str:
    """Render the per-country README content."""
    note = country_note(country, n_polygons) or "Standard coverage."
    return COUNTRY_README_TEMPLATE.format(
        country=country,
        n_polygons=n_polygons,
        extract_status=extract_status,
        pbf_date=pbf_date,
        geofabrik_url=geofabrik_url(country),
        country_note=note,
    )

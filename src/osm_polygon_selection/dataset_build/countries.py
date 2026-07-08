"""Regional sub-PBF metadata for large countries.

Some countries on Geofabrik are not provided as a single monolithic
PBF; instead the per-country page links out to a list of sub-PBFs
(administrative regions). When we walk ``raw/`` for these parents,
we must NOT treat each child as an independent country.

This module is a thin re-export over the canonical map in
:mod:`osm_polygon_selection.regional_pbf_meta`. The build pipeline
needs the full set (including ``haute-normandie``, ``bermuda``,
``falklands``) so it can filter sub-PBFs from ``raw/``.

For the single source of truth, see
:mod:`osm_polygon_selection.regional_pbf_meta`.
"""

from __future__ import annotations

from osm_polygon_selection.regional_pbf_meta import (
    ALL_REGIONAL_CANONICAL as ALL_REGIONAL,
    REGIONAL_SUB_PBFS_CANONICAL as REGIONAL_CHILDREN,
)

__all__ = ["REGIONAL_CHILDREN", "ALL_REGIONAL", "is_regional_child"]


def is_regional_child(country: str) -> bool:
    """Return True if ``country`` is a regional sub-PBF of some parent.

    Used by the dataset extraction pipeline to skip regional sub-PBFs
    when scanning ``raw/`` for independent country datasets.
    """
    return country in ALL_REGIONAL

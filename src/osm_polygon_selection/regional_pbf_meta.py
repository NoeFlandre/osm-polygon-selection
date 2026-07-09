"""Backwards-compat facade for the canonical regional sub-PBF map.

The canonical module lives at :mod:`osm_polygon_selection.pbf_meta.regional`.
This module re-exports ``REGIONAL_SUB_PBFS_CANONICAL`` and
``ALL_REGIONAL_CANONICAL`` so existing imports keep working.

New code should import from ``osm_polygon_selection.pbf_meta.regional``
directly.
"""

from __future__ import annotations

from osm_polygon_selection.pbf_meta.regional import (  # noqa: F401
    ALL_REGIONAL_CANONICAL,
    REGIONAL_SUB_PBFS_CANONICAL,
)

__all__ = ["ALL_REGIONAL_CANONICAL", "REGIONAL_SUB_PBFS_CANONICAL"]

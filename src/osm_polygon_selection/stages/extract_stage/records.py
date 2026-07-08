"""Per-polygon record building.

Two entry points:

- :func:`record` (full path: OSM Area -> JSONL row, uses osmium WKTFactory)
- :func:`record_from_wkt` (WKT -> JSONL row; unit-testable without osmium)

Both update the ``drops`` dict so callers can surface counts and
return 1 if a row was written, else 0.
"""

from __future__ import annotations

import json
import osmium
import shapely.wkt
from shapely.validation import make_valid  # noqa: F401  (kept for compat)

from osm_polygon_selection.core.geometry_utils import (
    approx_area_km2_lonlat,
    area_km2,
    is_polygon,  # noqa: F401  (kept for compat)
)
from osm_polygon_selection.stages.extract_stage.constants import (
    MAX_AREA_KM2,
    MAX_GEOMETRY_BYTES,
    MAX_VERTICES,
    MIN_AREA_KM2,
    VALIDATION_TIMEOUT_S,
)
from osm_polygon_selection.stages.extract_stage.timeout import (
    ValidationTimeout,
    call_with_timeout,
)

# Re-export so existing imports keep working.
__all__ = ["ValidationTimeout", "record", "record_from_wkt"]

# Module-level osmium WKT factory. Shared across all OSM Area objects.
_factory = osmium.geom.WKTFactory()


def _bump(drops: dict[str, int], key: str) -> None:
    drops[key] = drops.get(key, 0) + 1


def record(
    area: "osmium.osm.Area",
    fout,
    drops: dict[str, int],
) -> int:
    """Process one OSM Area object. Returns 1 if a row was written."""
    if not area.is_area():
        _bump(drops, "not_an_area")
        return 0
    try:
        wkt = _factory.create_multipolygon(area)
    except Exception:
        _bump(drops, "wkt_conversion_failed")
        return 0
    return record_from_wkt(area, wkt, fout, drops)


def record_from_wkt(
    area_area: osmium.osm.Area,
    wkt: str,
    fout,
    drops: dict[str, int],
) -> int:
    """Process a polygon given its WKT. Extracted from ``record`` so it
    can be unit-tested without mocking the osmium WKTFactory.
    """
    # Cheap size check before parsing. A pathological multipolygon can be
    # tens of MB of WKT and minutes of CPU to validate. Drop it now.
    if len(wkt) > MAX_GEOMETRY_BYTES:
        _bump(drops, "too_complex_wkt")
        return 0

    try:
        geom = shapely.wkt.loads(wkt)
    except Exception:
        _bump(drops, "wkt_parse_failed")
        return 0

    # Cheap shape filter. Don't call is_valid / make_valid here — we
    # only need to know if the result is a (Multi)Polygon, which we
    # can read directly from geom_type.
    if geom.geom_type not in ("Polygon", "MultiPolygon"):
        _bump(drops, "not_polygon")
        return 0

    # Vertex-count guard. C-level total count via shapely.get_num_coordinates
    # (~8x faster than iterating per-vertex in Python).
    try:
        import shapely as _shapely
        n_vertices = int(_shapely.get_num_coordinates(geom))
    except Exception:
        n_vertices = 0
    if n_vertices > MAX_VERTICES:
        _bump(drops, "too_complex_vertices")
        return 0

    approx_a = approx_area_km2_lonlat(geom)
    if approx_a < MIN_AREA_KM2 / 2:
        _bump(drops, "too_small")
        return 0
    a = area_km2(geom)
    if a < MIN_AREA_KM2:
        _bump(drops, "too_small")
        return 0
    if a > MAX_AREA_KM2:
        _bump(drops, "too_large")
        return 0

    # Clean invalid geometry with a hard cap. On timeout, keep the raw
    # geometry rather than dropping: the area/shape checks already passed.
    try:
        def _clean():
            return geom.buffer(0) if not geom.is_valid else geom
        geom = call_with_timeout(_clean, VALIDATION_TIMEOUT_S)
    except ValidationTimeout:
        _bump(drops, "validation_timeout")
        # Fall through: write the raw geometry.
    except Exception:
        _bump(drops, "validation_failed")
        return 0

    if geom.geom_type not in ("Polygon", "MultiPolygon"):
        _bump(drops, "not_polygon")
        return 0
    a = area_km2(geom)
    if a < MIN_AREA_KM2 or a > MAX_AREA_KM2:
        _bump(drops, "too_small" if a < MIN_AREA_KM2 else "too_large")
        return 0

    c = geom.centroid
    tags = [(k, v) for k, v in area_area.tags if k not in ("area", "type")]
    row = {
        "osm_id": area_area.id,
        "osm_type": "way" if area_area.from_way() else "relation",
        "geometry": geom.wkt,
        "centroid": [float(c.x), float(c.y)],
        "area_km2": a,
        "tags": [f"{k}={v}" for k, v in tags],
    }
    fout.write(json.dumps(row) + "\n")
    return 1

"""Stage 0: stream a PBF file, write closed-way + multipolygon polygons to JSONL.

Streams one polygon at a time and writes immediately, so memory use stays
flat regardless of PBF size (Europe 15GB -> ~50MB RAM, planet 70GB ->
same). This is essential: an in-memory accumulator would OOM on 8GB
machines at continent scale.

Filters applied per polygon (drop early, no allocation):
  - Must be a real area (closed way OR multipolygon relation)
  - Must be a Polygon or MultiPolygon (drop degenerate cases)
  - Area in [MIN_AREA_KM2, MAX_AREA_KM2]

What gets emitted per row: osm_id, osm_type, geometry (WKT), centroid
[lon, lat], area_km2, tags (list of "key=value" strings).
"""

import json
from pathlib import Path
from typing import cast

import osmium
import shapely.wkt
from shapely.validation import make_valid

from osm_polygon_selection.core.geometry_utils import area_km2, is_polygon

MIN_AREA_KM2 = 0.1
MAX_AREA_KM2 = 100.0

_factory = osmium.geom.WKTFactory()


def _record(area: osmium.osm.OSMObject, fout) -> int:
    """Process one OSM object. Write JSON line if it survives all filters.

    Returns 1 if a row was written, 0 otherwise.
    """
    if not area.is_area():
        return 0
    area_area = cast(osmium.osm.Area, area)
    try:
        wkt = _factory.create_multipolygon(area_area)
        geom = shapely.wkt.loads(wkt)
    except Exception:
        return 0

    if not geom.is_valid:
        geom = make_valid(geom)
    if not is_polygon(geom):
        return 0

    a = area_km2(geom)
    if a > MAX_AREA_KM2 or a < MIN_AREA_KM2:
        return 0

    c = geom.centroid
    tags = [(k, v) for k, v in area_area.tags if k not in ("area", "type")]
    row = {
        "osm_id": area.id,
        "osm_type": "way" if area_area.from_way() else "relation",
        "geometry": geom.wkt,
        "centroid": [float(c.x), float(c.y)],
        "area_km2": a,
        "tags": [f"{k}={v}" for k, v in tags],
    }
    fout.write(json.dumps(row) + "\n")
    return 1


def extract(pbf_path: Path, out_path: Path) -> int:
    """Stream a PBF, write each polygon to JSONL as it's parsed.

    Returns the number of polygons written.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out_path.open("w") as fout:
        for obj in osmium.FileProcessor(str(pbf_path)).with_areas():
            n += _record(cast(osmium.osm.OSMObject, obj), fout)
    return n

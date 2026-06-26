import json
from pathlib import Path

import osmium
import shapely
import shapely.wkt
from shapely.validation import make_valid

from osm_polygon_selection.geometry_utils import area_km2, is_polygon

MIN_AREA_KM2 = 0.1
MAX_AREA_KM2 = 100.0

_factory = osmium.geom.WKTFactory()


def _record(area: osmium.osm.Area, polygons: list[dict]) -> None:
    if not area.is_area():
        return
    try:
        wkt = _factory.create_multipolygon(area)
        geom = shapely.wkt.loads(wkt)
    except Exception:
        return

    if not geom.is_valid:
        geom = make_valid(geom)

    if not is_polygon(geom):
        return

    a = area_km2(geom)
    if a > MAX_AREA_KM2 or a < MIN_AREA_KM2:
        return

    c = geom.centroid

    tags = [(k, v) for k, v in area.tags if k not in ("area", "type")]
    polygons.append(
        {
            "osm_id": area.id,
            "osm_type": "relation" if area.from_way() is False else "way",
            "geometry": geom.wkt,
            "centroid": [float(c.x), float(c.y)],
            "area_km2": a,
            "tags": [f"{k}={v}" for k, v in tags],
        }
    )


def extract(pbf_path: Path, out_path: Path) -> int:
    """Streams a PBF, writes jsonl and returns the number of polygons"""
    polygons: list[dict] = []

    for area in osmium.FileProcessor(str(pbf_path)).with_areas():
        _record(area, polygons)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        for row in polygons:
            f.write(json.dumps(row) + "\n")
    return len(polygons)

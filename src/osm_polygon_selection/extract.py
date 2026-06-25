import json
from pathlib import Path

import osmium
import shapely.wkt
from shapely.validation import make_valid

from osm_polygon_selection.geometry_utils import area_km2, is_polygon

MIN_AREA_KM2 = 0.1  # 0.1 km^2 to drop noise
MAX_AREA_KM2 = 100  # 100 km^2 to filter out huge polygons
MIN_NODES_CLOSED_WAY = (
    4  # closed polygons need at least 4 refs (3 unique vertices + closing)
)


class PolygonHandler(osmium.SimpleHandler):
    def __init__(self) -> None:
        super().__init__()  # we are inheriting from SimpleHandler. We are reusing that class but adapting it
        self.way_factory = osmium.geo.WayFactory(self)
        self.area_factory = osmium.geo.AreaFactory(self.way_factory)
        self.polygons: list[dict] = []

    def way(self, w: osmium.osm.Way) -> None:
        if not w.tags:
            return  # if a way is having no tag then we drop it

        is_closed = w.is_closed()
        has_area_tag = "area" in w.tags
        if not (is_closed or has_area_tag):
            return  # if a way is not closed (first node == last node or area=yes) then we drop it

        if len(w.nodes) < MIN_NODES_CLOSED_WAY:
            return  # if a way has less than the minimum number of nodes allowed, we drop it

        try:
            area_obj = self.way_factory.create_way(
                w
            )  # we ask teh way factory to resolve this way refs to a polygon geometry
            geom = shapely.wkt.loads(
                area_obj.wkt
            )  # we use the WKT well known text standard geometry string format

        except Exception:
            return

        tags = [(k, v) for k, v in w.tags if k != "area"]
        self._record(geom, w.id, "way", tags)

    def relation(self, r: osmium.osm.Relation) -> None:
        if r.tags.get("type") != "multipolygon":
            return

        try:
            area_obj = self.area_factory.create_area(r)
            geom = shapely.wkt.loads(area_obj.wkt)

        except Exception:
            return

        tags = [(k, v) for k, v in r.tags if k != "type"]
        self._record(geom, r.id, "relation", tags)

    def _record(
        self,
        geom,
        osm_id: int,
        osm_type: str,
        tags: list[tuple],
    ) -> None:
        if not geom.is_valid:
            geom = make_valid(geom)

        if not is_polygon(geom):
            return

        a = area_km2(geom)
        if a < MIN_AREA_KM2 or a > MAX_AREA_KM2:
            return

        c = geom.centroid
        self.polygons.append(
            {
                "osm_id": osm_id,
                "osm_type": osm_type,
                "geometry": geom.wkt,
                "centroid": [float(c.x), float(c.y)],
                "area_km2": a,
                "tags": [f"{k}={v}" for k, v in tags],
            }
        )


def extract(pbf_path: Path, out_path: Path) -> int:
    handler = PolygonHandler()
    handler.apply_file(str(pbf_path))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        for row in handler.polygons:
            f.write(json.dumps(row) + "\n")
    return len(handler.polygons)

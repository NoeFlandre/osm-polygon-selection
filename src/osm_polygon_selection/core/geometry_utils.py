from typing import Callable

from pyproj import Transformer
from shapely import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

_PROJECTOR: Callable = Transformer.from_crs(
    "EPSG:4326", "EPSG:3857", always_xy=True
).transform


def area_km2(geom_lonlat: BaseGeometry) -> float:
    """
    Area of a lon / lat geometry in km^2

    We first apply a transformation from (lon, lat) to (x_meters, y_meters)
    and then compute the area on the projected geometry and divide by 1e6 to get km^2.

    """
    geom_m = transform(_PROJECTOR, geom_lonlat)
    return geom_m.area / 1_000_000.0


def is_polygon(geom: BaseGeometry) -> bool:
    """
    Keeps only geometries which are polygons and multipolygons
    """
    return isinstance(geom, (Polygon, MultiPolygon))


def centroid_lonlat(geom: BaseGeometry) -> list[float]:
    """
    Returns the lon/lat centroid of the polygon
    """

    c = geom.centroid
    return [float(c.x), float(c.y)]

from math import cos, radians
from typing import Callable

import shapely
from pyproj import Transformer
from shapely import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

_PROJECTOR: Callable = Transformer.from_crs(
    "EPSG:4326", "EPSG:3857", always_xy=True
).transform

# Approximate length of one degree of latitude in km (WGS84
# mean). Used by ``approx_area_km2_lonlat`` to convert degree²
# area to km² without a full reprojection.
_KM_PER_DEGREE_LAT = 111.32


def area_km2(geom_lonlat: BaseGeometry) -> float:
    """
    Area of a lon / lat geometry in km^2

    We first apply a transformation from (lon, lat) to (x_meters, y_meters)
    and then compute the area on the projected geometry and divide by 1e6 to get km^2.

    """
    geom_m = transform(_PROJECTOR, geom_lonlat)
    return geom_m.area / 1_000_000.0


def approx_area_km2_lonlat(geom_lonlat: BaseGeometry) -> float:
    """Fast approximate area in km² for a lon/lat geometry.

    Computes the area in degree² using the spherical excess
    formula (shoelace) and converts to km² by scaling with
    ``cos(centroid_lat) * KM_PER_DEGREE_LAT²``.

    This is the **first-pass filter** for the extract hot path
    (~5-10x faster than the full pyproj reprojection). It is
    not exact (the local scale varies with latitude and
    direction), but accurate to within a few percent for
    polygons up to a few km across, which is the vast majority
    of OSM polygons.

    For the final accepted-polygon area, the caller should
    use ``area_km2`` (full pyproj projection) to get the
    authoritative value.

    Args:
        geom_lonlat: a shapely geometry in lon/lat (EPSG:4326).

    Returns:
        Approximate area in km². Returns 0.0 for empty
        geometries and GeometryCollection (no area).
    """
    if geom_lonlat.is_empty:
        return 0.0

    # Centroid latitude for the cos(lat) correction. Cheap.
    c = geom_lonlat.centroid
    cos_lat = cos(radians(c.y))

    # Shoelace area in degree², summed over all rings (exterior
    # + interior for each polygon in the geometry). We iterate
    # over rings in Python (the per-polygon overhead is tiny
    # vs. the per-vertex cost we save on the numpy pass).
    import numpy as np
    deg2_area = 0.0
    try:
        if geom_lonlat.geom_type == "Polygon":
            rings = [
                geom_lonlat.exterior,  # type: ignore[attr-defined]
                *geom_lonlat.interiors,  # type: ignore[attr-defined]
            ]
        elif geom_lonlat.geom_type == "MultiPolygon":
            rings = []
            for poly in geom_lonlat.geoms:  # type: ignore[attr-defined]
                rings.append(poly.exterior)
                rings.extend(poly.interiors)
        else:
            return 0.0
    except Exception:
        # Defensive: malformed geometry. Return 0 so the
        # caller's pre-filter treats it as "unknown" (it'll
        # fall through to the full area_km2 path).
        return 0.0
    for ring in rings:
        try:
            # ``get_coordinates`` is the fastest path (C-level)
            # but raises on unclosed rings (which OSM WKT can
            # produce via osmium). Fall back to ``ring.coords``
            # (Python-level, ~10us) for malformed rings.
            coords = shapely.get_coordinates(ring, include_z=False)
        except Exception:
            try:
                coords = np.asarray(ring.coords, dtype=np.float64)
            except Exception:
                continue
        if coords.shape[0] < 3:
            continue
        x = coords[:, 0]
        y = coords[:, 1]
        # Ensure ring is closed for shoelace. If the last point
        # differs from the first, append the first.
        if x[0] != x[-1] or y[0] != y[-1]:
            x = np.append(x, x[0])
            y = np.append(y, y[0])
        # Shoelace sum = sum(x[i] * y[i+1] - x[i+1] * y[i]) for
        # i in 0..n-1, where x[n]=x[0] (closed ring).
        # Use numpy roll for the wrap.
        x_next = np.roll(x, -1)
        y_next = np.roll(y, -1)
        deg2_area += abs(float(np.sum(x * y_next - x_next * y)) / 2.0)

    return deg2_area * (cos_lat * _KM_PER_DEGREE_LAT ** 2)


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

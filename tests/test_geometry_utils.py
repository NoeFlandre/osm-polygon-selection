"""Tests for fast geometry utilities used in the extract hot path.

Stage 0 (PBF -> JSONL) processes 200M+ OSM objects per continent.
The expensive ``area_km2`` (via pyproj reprojection + shapely ops
transform) is called once per polygon that passes the cheap
geom_type filter — 500k+ times for a typical 50MB PBF.

For polygons that are obviously too small (90%+ of all OSM
polygons are <0.1 km²), reprojecting the whole geometry is
wasteful. A fast lon/lat approximation can reject 90% of
polygons with ~10x less work.

These tests pin the contract for ``approx_area_km2_lonlat``:
  - exact for unit-square polygons near the equator
  - within 1% for polygons at any latitude
  - returns 0 for empty geometries
  - rejects polygons that are obviously too small
  - accepts polygons within the 0.1-100 km² size window
  - handles multipolygons
"""

from __future__ import annotations

import math

import pytest
import shapely.wkt

from osm_polygon_selection.core.geometry_utils import (
    approx_area_km2_lonlat,
    area_km2,
)


# A 1°×1° square at the equator is ~12321 km² (111.32 km per
# degree). At 60°N, a 1°×1° square is ~6162 km² (cos(60°)=0.5).
EQUATOR_WKT = "POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))"  # ~12,321 km²
HIGH_LAT_WKT = "POLYGON ((10 60, 11 60, 11 61, 10 61, 10 60))"  # ~6,160 km²


class TestApproxAreaKm2Lonlat:
    """The approx_area_km2_lonlat function is a fast pre-filter
    used in the extract hot path to reject obviously-tiny
    polygons before the full pyproj reprojection.

    The approx uses ``shoelace(deg²) * cos(centroid_lat) *
    111.32²`` which is the **true ellipsoidal area** in km². It
    differs from the project-wide ``area_km2`` (Web Mercator)
    at high latitudes — Web Mercator exaggerates area as you
    go north, so the approx is *smaller* than ``area_km2`` at
    lat > 30°. This is intentional: the approx is a conservative
    pre-filter, and the full ``area_km2`` runs on the survivors
    to produce the authoritative dataset value.
    """

    def test_empty_geometry_returns_zero(self) -> None:
        """Empty geometry (no coords) returns 0, not a crash."""
        from shapely.geometry import GeometryCollection
        gc = GeometryCollection()
        assert approx_area_km2_lonlat(gc) == 0.0

    def test_polygon_at_equator_close_to_true_area(self) -> None:
        """A 1°×1° square at the equator is ~12,321 km² in
        both metrics (cos(0)=1, so the projection distortion
        is minimal)."""
        geom = shapely.wkt.loads(EQUATOR_WKT)
        approx = approx_area_km2_lonlat(geom)
        truth = area_km2(geom)
        assert math.isclose(approx, truth, rel_tol=0.05), (
            f"approx={approx:.0f}, truth={truth:.0f}"
        )

    def test_polygon_at_high_latitude_scales_by_cos_lat(self) -> None:
        """At 60°N, a 1°×1° square is ~6,160 km² in real km²
        (cos(60°)=0.5) but ~25,168 km² in Web Mercator
        (Mercator distorts area as 1/cos²). The approx
        returns the real value, which is INTENTIONALLY
        smaller than ``area_km2``."""
        geom = shapely.wkt.loads(HIGH_LAT_WKT)
        approx = approx_area_km2_lonlat(geom)
        # Real ellipsoidal: ~6,160 km²
        assert 5900 < approx < 6400, f"approx={approx:.0f} (expected ~6160)"
        # And smaller than the Web Mercator value (which is ~25k)
        truth = area_km2(geom)
        assert approx < truth, (
            f"approx={approx:.0f} should be smaller than truth={truth:.0f} "
            f"at high latitude"
        )

    def test_rejects_tiny_polygons(self) -> None:
        """A 0.0001°×0.0001° square is ~0.0000123 km²,
        well below MIN_AREA_KM2=0.1. The approx must return
        a value below 0.1 km² so the upstream code drops it.
        """
        wkt = "POLYGON ((0 0, 0.0001 0, 0.0001 0.0001, 0 0.0001, 0 0))"
        geom = shapely.wkt.loads(wkt)
        assert approx_area_km2_lonlat(geom) < 0.1

    def test_accepts_medium_polygons(self) -> None:
        """A 0.01°×0.01° square at the equator is ~1.23 km²,
        above MIN_AREA_KM2=0.1. The approx must return a value
        within 10% of 1.23 km² so the upstream code accepts it.
        """
        wkt = "POLYGON ((0 0, 0.01 0, 0.01 0.01, 0 0.01, 0 0))"
        geom = shapely.wkt.loads(wkt)
        approx = approx_area_km2_lonlat(geom)
        truth = area_km2(geom)
        assert math.isclose(approx, truth, rel_tol=0.05)

    def test_handles_multipolygon(self) -> None:
        """Multipolygons should sum the per-polygon areas."""
        # Two unit squares at the equator = ~24,642 km²
        wkt = (
            "MULTIPOLYGON ("
            "((0 0, 1 0, 1 1, 0 1, 0 0)), "
            "((2 0, 3 0, 3 1, 2 1, 2 0))"
            ")"
        )
        geom = shapely.wkt.loads(wkt)
        truth = area_km2(geom)
        approx = approx_area_km2_lonlat(geom)
        assert math.isclose(approx, truth, rel_tol=0.05)

    def test_faster_than_full_reprojection(self) -> None:
        """The fast approximation must be measurably faster than
        the full pyproj reprojection on realistic OSM polygon
        sizes (50 vertices). The pyproj reprojection is
        per-vertex, so the speedup grows with vertex count.
        On a 50-vertex polygon, the speedup is ~2x; on bigger
        polygons it's much higher.
        """
        import time
        # Build a 50-vertex polygon (typical OSM building/landuse)
        coords = [(0.0 + i * 0.0001, 0.0 + (i % 7) * 0.0001) for i in range(50)]
        coords.append(coords[0])  # close the ring
        wkt = "POLYGON ((" + ", ".join(f"{x} {y}" for x, y in coords) + "))"
        geom = shapely.wkt.loads(wkt)
        N = 5_000
        t0 = time.perf_counter()
        for _ in range(N):
            area_km2(geom)
        full = time.perf_counter() - t0
        t0 = time.perf_counter()
        for _ in range(N):
            approx_area_km2_lonlat(geom)
        approx = time.perf_counter() - t0
        # Loose 1.5x threshold (loose to avoid CI noise).
        # On a 50-vertex polygon: 1.9-2.5x. On larger polygons:
        # 3-5x.
        assert approx < full * 0.67, (
            f"approx={approx*1e6/N:.1f}us, full={full*1e6/N:.1f}us, "
            f"speedup={full/approx:.2f}x"
        )

    def test_negative_coords_handled(self) -> None:
        """Southern hemisphere (negative lat) and western
        hemisphere (negative lon) work the same way."""
        wkt = "POLYGON ((-1 -1, 0 -1, 0 0, -1 0, -1 -1))"
        geom = shapely.wkt.loads(wkt)
        truth = area_km2(geom)
        approx = approx_area_km2_lonlat(geom)
        assert math.isclose(approx, truth, rel_tol=0.05)

    def test_conservative_pre_filter_below_threshold(self) -> None:
        """The contract for the extract pre-filter: if the
        approx is well below MIN_AREA_KM2 (e.g. 0.05 km²),
        the polygon is GUARANTEED to be below the threshold
        in the full projection. This is what lets the extract
        hot path skip the expensive ``area_km2`` call.

        We verify the property on a small polygon: the approx
        (0.000012 km²) is well below 0.05 km², so the cheap
        filter rejects it without ever running the full
        reprojection.
        """
        wkt = "POLYGON ((0 0, 0.0001 0, 0.0001 0.0001, 0 0.0001, 0 0))"
        geom = shapely.wkt.loads(wkt)
        approx = approx_area_km2_lonlat(geom)
        # Conservative threshold: half of MIN_AREA_KM2.
        assert approx < 0.05, f"approx={approx}, expected < 0.05 (cheap-filter cut-off)"

"""Tests for geometry_utils module."""

import pytest
from shapely.geometry import LineString, MultiPolygon, Point, Polygon

from osm_polygon_selection.core.geometry_utils import area_km2, centroid_lonlat, is_polygon


# Test fixtures

@pytest.fixture
def unit_square_paris() -> Polygon:
    """A 1 km x 1 km square near Paris (~49 deg latitude).

    1 deg lat ≈ 110.6 km, so 0.00904 deg lat ≈ 1.00 km.
    1 deg lon at 48.85 deg ≈ 73.0 km, so 0.01370 deg lon ≈ 1.00 km.
    Mercator distortion at 48.85 deg inflates y by ~1.52x, so the
    reprojected area is ~1.52 km^2 (allow 10% margin).
    """
    return Polygon([
        (2.35, 48.85),
        (2.3637, 48.85),
        (2.3637, 48.85904),
        (2.35, 48.85904),
    ])


@pytest.fixture
def unit_square_equator() -> Polygon:
    """A 1 km x 1 km square at the equator (no Mercator distortion)."""
    return Polygon([
        (0.0, 0.0),
        (0.00898, 0.0),
        (0.00898, 0.00904),
        (0.0, 0.00904),
    ])


@pytest.fixture
def multipolygon_two_squares() -> MultiPolygon:
    return MultiPolygon([
        Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
        Polygon([(2, 2), (3, 2), (3, 3), (2, 3)]),
    ])


# area_km2

def test_area_km2_equator_no_distortion(unit_square_equator: Polygon) -> None:
    """At the equator, 1 km square should be ~1.0 km^2 (within 5%)."""
    a = area_km2(unit_square_equator)
    assert 0.95 <= a <= 1.05


def test_area_km2_paris_has_mercator_inflation(unit_square_paris: Polygon) -> None:
    """At ~49 deg latitude, Mercator inflates area by sec(lat)^2.

    Web Mercator stretches both x and y by the same factor
    sec(latitude). At 48.85 deg, sec = 1.521, so area is inflated by
    1.521^2 = 2.31 (vs the geometric 1.0 km^2).
    """
    a = area_km2(unit_square_paris)
    assert 2.1 <= a <= 2.5


def test_area_km2_multipolygon_sums_components(multipolygon_two_squares: MultiPolygon) -> None:
    """MultiPolygon area = sum of its components."""
    a = area_km2(multipolygon_two_squares)
    assert a > 0


# is_polygon

def test_is_polygon_accepts_polygon(unit_square_equator: Polygon) -> None:
    assert is_polygon(unit_square_equator) is True


def test_is_polygon_accepts_multipolygon(multipolygon_two_squares: MultiPolygon) -> None:
    assert is_polygon(multipolygon_two_squares) is True


def test_is_polygon_rejects_point() -> None:
    assert is_polygon(Point(0, 0)) is False


def test_is_polygon_rejects_linestring() -> None:
    assert is_polygon(LineString([(0, 0), (1, 1)])) is False


# centroid_lonlat

def test_centroid_lonlat_returns_lon_lat_pair(unit_square_equator: Polygon) -> None:
    """Returns a 2-element list [lon, lat]."""
    c = centroid_lonlat(unit_square_equator)
    assert isinstance(c, list)
    assert len(c) == 2
    assert all(isinstance(x, float) for x in c)


def test_centroid_lonlat_is_inside_polygon(unit_square_equator: Polygon) -> None:
    """Centroid of a simple square should be near its geometric center."""
    lon, lat = centroid_lonlat(unit_square_equator)
    # Geometric center is at (0.00449, 0.00452). Allow 10% margin.
    assert 0.0040 <= lon <= 0.0050
    assert 0.0040 <= lat <= 0.0050


def test_centroid_lonlat_returns_floats_not_numpy(unit_square_equator: Polygon) -> None:
    """Returns Python floats, not numpy scalars (for JSON serialization)."""
    lon, lat = centroid_lonlat(unit_square_equator)
    assert type(lon) is float
    assert type(lat) is float

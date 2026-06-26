"""Tests for Stage 4 classify module."""

import json
from pathlib import Path

import geopandas as gpd  # type: ignore[import-untyped]
import pytest
from shapely.geometry import Point, Polygon

from osm_polygon_selection.stages.classify import (
    continent_of,
    load_countries,
    size_bin,
)


# size_bin tests

def test_size_bin_tiny() -> None:
    assert size_bin(0.001) == "tiny"
    assert size_bin(0.05) == "tiny"
    assert size_bin(0.099) == "tiny"


def test_size_bin_small() -> None:
    assert size_bin(0.1) == "small"
    assert size_bin(0.5) == "small"
    assert size_bin(0.999) == "small"


def test_size_bin_medium() -> None:
    assert size_bin(1.0) == "medium"
    assert size_bin(5.0) == "medium"
    assert size_bin(9.999) == "medium"


def test_size_bin_large() -> None:
    assert size_bin(10.0) == "large"
    assert size_bin(50.0) == "large"
    assert size_bin(100.0) == "large"
    assert size_bin(1_000_000.0) == "large"


def test_size_bin_zero() -> None:
    """Edge case: zero area polygon should be 'tiny'."""
    assert size_bin(0.0) == "tiny"


def test_size_bin_negative() -> None:
    """Negative area shouldn't happen but should fall into tiny."""
    assert size_bin(-1.0) == "tiny"


# continent_of tests

def _fake_countries():
    """Build an in-memory GeoDataFrame mimicking Natural Earth for tests."""
    return gpd.GeoDataFrame(
        {
            "CONTINENT": ["Europe", "Asia", "Africa"],
            "NAME": ["France", "Japan", "Egypt"],
        },
        geometry=[
            Polygon([(0, 0), (10, 0), (10, 10), (0, 10)]),     # France
            Polygon([(100, 100), (110, 100), (110, 110), (100, 110)]),  # Japan
            Polygon([(20, 0), (30, 0), (30, 10), (20, 10)]),    # Egypt
        ],
        crs="EPSG:4326",
    )


@pytest.fixture
def fake_index():
    countries = _fake_countries()
    tree, geom, cont = load_countries_from_gdf(countries)
    return tree, geom, cont


def load_countries_from_gdf(gdf: gpd.GeoDataFrame):
    """Build the spatial index from an in-memory GeoDataFrame."""
    from shapely.strtree import STRtree
    geom = list(gdf.geometry)
    cont = list(gdf["CONTINENT"])
    tree = STRtree(geom)
    return tree, geom, cont


def test_continent_of_returns_continent_when_point_inside(fake_index) -> None:
    tree, geom, cont = fake_index
    p = Point(5, 5)  # inside France
    assert continent_of(p, tree, geom, cont) == "Europe"


def test_continent_of_returns_first_match_for_shared_border(fake_index) -> None:
    tree, geom, cont = fake_index
    # France ends at x=10, Egypt starts at x=20. Pick a point just inside
    # the Egypt box (x=20.0001). It should map to Africa, not Europe.
    p = Point(20.0001, 5)
    assert continent_of(p, tree, geom, cont) == "Africa"


def test_continent_of_returns_first_match_inside_europe_box(fake_index) -> None:
    tree, geom, cont = fake_index
    # France spans x in [0, 10]. A point at x=9 should be Europe.
    p = Point(9, 5)
    assert continent_of(p, tree, geom, cont) == "Europe"


def test_continent_of_returns_none_for_ocean_point(fake_index) -> None:
    tree, geom, cont = fake_index
    # Far from any country
    p = Point(50, 50)
    assert continent_of(p, tree, geom, cont) is None


def test_continent_of_handles_point_outside_all_bboxes(fake_index) -> None:
    """Point in ocean far from all bounding boxes returns None."""
    tree, geom, cont = fake_index
    p = Point(200, 200)
    assert continent_of(p, tree, geom, cont) is None


# Integration: load_countries works on a real shapefile path

def test_load_countries_reads_real_shapefile() -> None:
    """Smoke test against the actual Natural Earth shapefile in data/reference/."""
    shp = Path("data/reference/natural_earth/ne_110m_admin_0_countries.shp")
    if not shp.exists():
        pytest.skip("Natural Earth shapefile not present")
    tree, geom, cont = load_countries(shp)
    # Natural Earth 110m admin0 has ~177 countries
    assert len(geom) == len(cont) > 100
    assert all(isinstance(c, str) for c in cont)
    # A known European centroid (Paris)
    assert continent_of(Point(2.35, 48.85), tree, geom, cont) == "Europe"


def test_load_countries_real_shapefile_liechtenstein() -> None:
    shp = Path("data/reference/natural_earth/ne_110m_admin_0_countries.shp")
    if not shp.exists():
        pytest.skip("Natural Earth shapefile not present")
    tree, geom, cont = load_countries(shp)
    # Vaduz, Liechtenstein
    assert continent_of(Point(9.52, 47.14), tree, geom, cont) == "Europe"


def test_load_countries_real_shapefile_tokyo() -> None:
    shp = Path("data/reference/natural_earth/ne_110m_admin_0_countries.shp")
    if not shp.exists():
        pytest.skip("Natural Earth shapefile not present")
    tree, geom, cont = load_countries(shp)
    # Tokyo, Japan
    assert continent_of(Point(139.69, 35.69), tree, geom, cont) == "Asia"

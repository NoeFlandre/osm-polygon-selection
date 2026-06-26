"""Stage 4: assign continent to each polygon via spatial lookup.

Uses a Natural Earth admin0 shapefile (country polygons with continent
labels) and a Shapely STRtree for fast point-in-polygon queries.
"""

import json
from pathlib import Path

import geopandas as gpd  # type: ignore[import-untyped]  # stubs unavailable
from shapely.geometry import Point
from shapely.strtree import STRtree

# Sentinel for polygons whose centroid does not fall in any country shape
# (typically ocean polygons). Downstream stages can drop or bucket these.
OCEAN_LABEL = None

# Size bin upper bounds (km²), in ascending order. The number of bounds
# is one less than the number of bins. The last bin is open-ended.
SIZE_BIN_BOUNDS_KM2: list[float] = [0.1, 1.0, 10.0]

# Bin names, ordered from smallest to largest.
SIZE_BIN_NAMES: list[str] = ["tiny", "small", "medium", "large"]


def size_bin(area_km2: float) -> str:
    """Map an area in km² to a size bin name."""
    for upper, name in zip(SIZE_BIN_BOUNDS_KM2, SIZE_BIN_NAMES):
        if area_km2 < upper:
            return name
    return SIZE_BIN_NAMES[-1]


def continent_of(
    point: Point,
    tree: STRtree,
    countries_geom: list,
    countries_continent: list,
) -> str | None:
    """Return the continent containing point, or OCEAN_LABEL if none."""
    idx = tree.query(point)
    for i in idx:
        if countries_geom[i].contains(point):
            return countries_continent[i]
    return OCEAN_LABEL


def load_countries(shp_path: Path) -> tuple[STRtree, list, list]:
    """Build the spatial index + parallel lookup lists from a shapefile."""
    countries = gpd.read_file(shp_path)
    countries_geom = list(countries.geometry)
    countries_continent = list(countries["CONTINENT"])
    tree = STRtree(countries_geom)
    return tree, countries_geom, countries_continent


def classify_jsonl(
    jsonl_in: Path, shp_path: Path, jsonl_out: Path,
) -> int:
    """Stream polygons in, attach continent, write out. Returns count."""
    tree, countries_geom, countries_continent = load_countries(shp_path)

    jsonl_out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with jsonl_in.open() as fin, jsonl_out.open("w") as fout:
        for line in fin:
            row = json.loads(line)
            lon, lat = row["centroid"]
            row["continent"] = continent_of(
                Point(lon, lat), tree, countries_geom, countries_continent,
            )
            row["size_bin"] = size_bin(row["area_km2"])
            fout.write(json.dumps(row) + "\n")
            n += 1
    return n

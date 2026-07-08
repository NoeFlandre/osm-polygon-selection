"""Tests for `osm_polygon_selection.dataset_build.readme`.

The package function is a pure renderer: given an out_dir with
sample/per_country/combined subdirs, the function returns the README
text. The test pins the byte-exact output against a frozen fixture
captured in tests/fixtures/readme/dataset_write_readme_minimal.md.
"""

from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "readme"
    / "dataset_write_readme_minimal.md"
)


def _build_minimal_out_dir(tmp: Path) -> Path:
    """Build the on-disk fixture that write_readme expects."""
    out = tmp
    (out / "sample").mkdir()
    (out / "splits").mkdir()
    (out / "per_country" / "monaco").mkdir(parents=True)
    (out / "per_country" / "liechtenstein").mkdir(parents=True)
    (out / "combined").mkdir()
    (out / "preview").mkdir()

    pq.write_table(
        pa.table({
            "osm_id": [1],
            "osm_type": ["way"],
            "centroid_lon": [9.5],
            "centroid_lat": [47.05],
            "area_km2": [0.5],
            "tags": [["landuse=forest"]],
            "matched_tag": ["landuse=forest"],
            "continent": ["europe"],
            "size_bin": ["small"],
            "country": ["monaco"],
            "extract_status": ["clean"],
            "pbf_date": ["2026-01-01"],
            "geometry_wkt": ["POLYGON((9.5 47.05, 9.51 47.05, 9.51 47.06, 9.5 47.06, 9.5 47.05))"],
        }),
        out / "per_country" / "monaco" / "monaco.parquet",
    )
    pq.write_table(
        pa.table({
            "osm_id": [42],
            "osm_type": ["way"],
            "centroid_lon": [9.55],
            "centroid_lat": [47.10],
            "area_km2": [0.3],
            "tags": [["natural=wood", "landuse=forest"]],
            "matched_tag": ["natural=wood"],
            "continent": ["europe"],
            "size_bin": ["small"],
            "country": ["liechtenstein"],
            "extract_status": ["clean"],
            "pbf_date": ["2026-01-01"],
            "geometry_wkt": ["POLYGON((9.55 47.10, 9.56 47.10, 9.56 47.11, 9.55 47.11, 9.55 47.10))"],
        }),
        out / "per_country" / "liechtenstein" / "liechtenstein.parquet",
    )
    n = 170
    pq.write_table(
        pa.table({
            "osm_id": list(range(n)),
            "osm_type": ["way"] * n,
            "centroid_lon": [0.0 + i * 0.01 for i in range(n)],
            "centroid_lat": [0.0 + i * 0.01 for i in range(n)],
            "area_km2": [0.5 if i < 100 else 5.0 if i < 150 else 50.0 for i in range(n)],
            "tags": [["landuse=forest"]] * n,
            "matched_tag": ["landuse=forest"] * n,
            "continent": ["europe"] * n,
            "size_bin": ["small" if i < 100 else "medium" if i < 150 else "large" for i in range(n)],
            "country": ["x"] * n,
            "extract_status": ["clean"] * n,
            "pbf_date": ["2026-01-01"] * n,
            "geometry_wkt": [None] * n,
        }),
        out / "combined" / "all_world.parquet",
    )
    (out / "sample" / "sample_map.jsonl").write_text(
        json.dumps({
            "osm_id": 42,
            "country": "liechtenstein",
            "size_bin": "small",
            "centroid_lon": 9.55,
            "centroid_lat": 47.10,
        }) + "\n"
    )
    return out


def test_write_readme_byte_exact(tmp_path: Path) -> None:
    """write_readme(out_dir, ...) == frozen fixture, full string equality."""
    from osm_polygon_selection.dataset_build.readme import write_readme

    out = _build_minimal_out_dir(tmp_path)
    countries_done = [
        {"country": "monaco", "n_polygons": 100, "extract_status": "clean", "pbf_date": "2026-01-01"},
        {"country": "liechtenstein", "n_polygons": 70, "extract_status": "clean", "pbf_date": "2026-01-01"},
    ]
    write_readme(
        out_dir=out,
        countries_done=countries_done,
        total_polygons=170,
        pipeline_version="v0.1.0",
        git_sha_value="abc1234",
        built_at="2026-01-01T00:00:00",
        geometry_encoding="wkt",
    )
    actual = (out / "README.md").read_text()
    expected = FIXTURE.read_text()
    assert actual == expected, (
        f"write_readme output drifted from the frozen fixture.\n"
        f"Actual: {len(actual)} bytes, Expected: {len(expected)} bytes.\n"
        f"Run `uv run python tests/fixtures/readme/_generator.py` to refresh."
    )

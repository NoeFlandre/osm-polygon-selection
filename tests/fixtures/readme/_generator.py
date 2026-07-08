"""Capture dataset_build.readme.write_readme golden output.

This script regenerates the test/fixtures/readme/dataset_write_readme_minimal.md
fixture. It is run manually when the README format is intentionally
changed (Phase 2c et seq). The fixture is the byte-exact contract.

Usage:
    uv run python tests/fixtures/readme/_generator.py
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from osm_polygon_selection.dataset_build.readme import write_readme

FROZEN_DATE = "2026-01-01T00:00:00"
PIPELINE_VERSION = "v0.1.0"
GIT_SHA = "abc1234"
GEOMETRY_ENCODING = "wkt"


def _build_minimal_root(tmp: Path) -> Path:
    """Build a minimal out_dir so write_readme has a sample + per-country parquet."""
    out = tmp
    (out / "sample").mkdir()
    (out / "splits").mkdir()
    (out / "per_country" / "monaco").mkdir(parents=True)
    (out / "per_country" / "liechtenstein").mkdir(parents=True)
    (out / "combined").mkdir()
    (out / "preview").mkdir()

    # A tiny per-country parquet for monaco (used by the example row).
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

    # Tiny liechtenstein parquet for the example row (with natural=wood).
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

    # Combined parquet: 100 small + 50 medium + 20 large.
    n = 170
    size_bin = ["small" if i < 100 else "medium" if i < 150 else "large" for i in range(n)]
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
            "size_bin": size_bin,
            "country": ["x"] * n,
            "extract_status": ["clean"] * n,
            "pbf_date": ["2026-01-01"] * n,
            "geometry_wkt": [None] * n,
        }),
        out / "combined" / "all_world.parquet",
    )

    # Sample JSONL: one row from liechtenstein so the example-row path picks it.
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


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        root = _build_minimal_root(out)

        countries_done = [
            {"country": "monaco", "n_polygons": 100, "extract_status": "clean", "pbf_date": "2026-01-01"},
            {"country": "liechtenstein", "n_polygons": 70, "extract_status": "clean", "pbf_date": "2026-01-01"},
        ]

        write_readme(
            out_dir=root,
            countries_done=countries_done,
            total_polygons=170,
            pipeline_version=PIPELINE_VERSION,
            git_sha_value=GIT_SHA,
            built_at=FROZEN_DATE,
            geometry_encoding=GEOMETRY_ENCODING,
        )

        out_path = Path("tests/fixtures/readme/dataset_write_readme_minimal.md")
        out_path.write_text((root / "README.md").read_text())
        print(f"wrote {out_path} ({out_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

"""Shared helpers for split tests."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
MAKE_SPLIT = SCRIPTS_DIR / "make_split.py"


def _load_make_split():
    spec = importlib.util.spec_from_file_location("make_split", MAKE_SPLIT)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load {MAKE_SPLIT}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["make_split"] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_country_table(country: str, n: int, base_id: int = 1) -> pa.Table:
    return pa.table(
        {
            "osm_id": np.arange(base_id, base_id + n, dtype=np.int64),
            "osm_type": ["way"] * n,
            "centroid_lon": np.linspace(0.0, 1.0, n, dtype=np.float64),
            "centroid_lat": np.linspace(0.0, 1.0, n, dtype=np.float64),
            "area_km2": np.full(n, 1.0, dtype=np.float64),
            "tags": [["landuse=forest"]] * n,
            "matched_tag": ["landuse=forest"] * n,
            "continent": ["Europe"] * n,
            "size_bin": ["small"] * n,
            "country": [country] * n,
            "extract_status": ["clean"] * n,
            "pbf_date": ["2026-06-26"] * n,
            "geometry_wkt": [f"POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))"] * n,
        }
    )


def _make_split_dataset(
    tmp_path: Path,
    countries_and_counts: dict[str, int],
) -> Path:
    root = tmp_path / "dataset"
    (root / "per_country").mkdir(parents=True)
    (root / "splits").mkdir(parents=True)
    (root / "combined").mkdir(parents=True)
    for c, n in countries_and_counts.items():
        cd = root / "per_country" / c
        cd.mkdir()
        pq.write_table(_make_country_table(c, n), cd / f"{c}.parquet")
    manifest = {
        "version": "v0.0.0-test",
        "total_polygons": sum(countries_and_counts.values()),
        "n_countries": len(countries_and_counts),
        "countries": [
            {"country": c, "n_polygons": n, "extract_status": "clean",
             "pbf_date": "2026-06-26"}
            for c, n in countries_and_counts.items()
        ],
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return root

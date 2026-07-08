"""Characterization tests for `scripts/sample_for_map.py` behavior we MUST preserve.

These pin:

- The four config constants (FLOOR, CAP, POWER, GEO_COLS).
- Module-level `random.seed(42)` does NOT influence grid_sample_country
  (grid_sample_country takes a local `rng` parameter).
- Dataset root discovery: env var > RuntimeConfig > script default.
- Deterministic output: same parquet fixture + same target_n + same
  rng seed -> same set of selected ids.
"""

from __future__ import annotations

import random
import importlib.util
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq


def _load_sample_for_map_module():
    """Import scripts/sample_for_map.py as a module."""
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "sample_for_map.py"
    spec = importlib.util.spec_from_file_location("sample_for_map_under_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_config_constants_match_current_values() -> None:
    """FLOOR, CAP, POWER, GEO_COLS must keep their current numeric values."""
    sfm = _load_sample_for_map_module()
    assert sfm.FLOOR == 8
    assert sfm.CAP == 200
    assert abs(sfm.POWER - 0.4) < 1e-9
    assert sfm.GEO_COLS == ["centroid_lon", "centroid_lat"]


def test_module_level_random_seed_does_not_affect_grid_sample(tmp_path: Path) -> None:
    """Pin that grid_sample_country's determinism comes from its own rng,
    not from any module-level `random.seed(42)` call.

    Strategy: call grid_sample_country twice on the same fixture under
    different global random states but with the same local
    random.Random(42). Selected osm_ids must be identical. Only after
    this test passes may random.seed(42) be safely removed.
    """
    lons = [10.0 + 0.001 * i for i in range(500)] + [11.0 + 0.001 * i for i in range(500)]
    lats = [50.0 + 0.001 * i for i in range(500)] + [51.0 + 0.001 * i for i in range(500)]
    pq_path = tmp_path / "x.parquet"
    _make_synthetic_country_parquet(pq_path, lons, lats)

    # First run: global state seeded with 1.
    random.seed(1)
    np.random.seed(1)
    sfm = _load_sample_for_map_module()
    rng1 = random.Random(42)
    sample1 = sfm.grid_sample_country(pq_path, target_n=64, rng=rng1)
    ids1 = sorted(r["osm_id"] for r in sample1)

    # Second run: very different global state, same local rng seed.
    random.seed(999_999_999)
    np.random.seed(999_999_999)
    sfm2 = _load_sample_for_map_module()
    rng2 = random.Random(42)
    sample2 = sfm2.grid_sample_country(pq_path, target_n=64, rng=rng2)
    ids2 = sorted(r["osm_id"] for r in sample2)

    assert ids1 == ids2, (
        "grid_sample_country output differs when global random state changes; "
        "it must be a pure function of (parquet, target_n, local rng)."
    )


def _make_synthetic_country_parquet(path: Path, lons: list[float], lats: list[float]) -> None:
    """Write a small parquet file with the columns sample_for_map expects."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n = len(lons)
    table = pa.table(
        {
            "osm_id": list(range(n)),
            "area_km2": [1.0] * n,
            "continent": ["europe"] * n,
            "matched_tag": ["landuse=forest"] * n,
            "centroid_lon": lons,
            "centroid_lat": lats,
            "country": ["x"] * n,
            "size_bin": ["small"] * n,
        }
    )
    pq.write_table(table, path)


def test_grid_sample_country_is_deterministic(tmp_path: Path) -> None:
    """Same fixture + same target_n + same rng seed -> same selected ids."""
    sfm = _load_sample_for_map_module()

    lons = [10.0 + 0.001 * i for i in range(500)] + [11.0 + 0.001 * i for i in range(500)]
    lats = [50.0 + 0.001 * i for i in range(500)] + [51.0 + 0.001 * i for i in range(500)]
    pq_path = tmp_path / "x.parquet"
    _make_synthetic_country_parquet(pq_path, lons, lats)

    rng1 = random.Random(42)
    rng2 = random.Random(42)
    sample1 = sfm.grid_sample_country(pq_path, target_n=64, rng=rng1)
    sample2 = sfm.grid_sample_country(pq_path, target_n=64, rng=rng2)
    ids1 = sorted(r["osm_id"] for r in sample1)
    ids2 = sorted(r["osm_id"] for r in sample2)
    assert ids1 == ids2
    assert len(ids1) <= 64


def test_dataset_root_env_var_overrides_runtime_config(monkeypatch, tmp_path: Path) -> None:
    """$OSM_DATASET_DIR overrides dataset_root() result for the script."""
    monkeypatch.setenv("OSM_DATASET_DIR", str(tmp_path / "override-dataset"))
    sfm = _load_sample_for_map_module()
    assert sfm.DATASET_ROOT == tmp_path / "override-dataset"
    assert sfm.DATASET_ROOT.name == "override-dataset"

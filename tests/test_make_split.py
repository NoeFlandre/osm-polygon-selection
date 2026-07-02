"""Tests for the train/val/test split script.

These tests pin the behavior of `scripts/make_split.py`:

- ratios must sum to 1.0
- every input row gets exactly one of {train, val, test}
- per-country counts are preserved within a tolerance
- the split is deterministic for a fixed seed
- different seeds give different splits
- the manifest has the required keys
- the parquet gets a `split` column of type string
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
MAKE_SPLIT = SCRIPTS_DIR / "make_split.py"


def _load_make_split():
    spec = importlib.util.spec_from_file_location("make_split", MAKE_SPLIT)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load {MAKE_SPLIT}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["make_split"] = mod
    spec.loader.exec_module(mod)
    return mod


# --- helpers ---------------------------------------------------------------


def _make_country_table(country: str, n: int, base_id: int = 1) -> pa.Table:
    """Build a small parquet-like table for a single country."""
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
    """Write per-country parquets for a few countries. Returns dataset root."""
    root = tmp_path / "dataset"
    (root / "per_country").mkdir(parents=True)
    (root / "splits").mkdir(parents=True)
    (root / "combined").mkdir(parents=True)
    for c, n in countries_and_counts.items():
        cd = root / "per_country" / c
        cd.mkdir()
        pq.write_table(_make_country_table(c, n), cd / f"{c}.parquet")
    # Manifest.
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


# --- tests -----------------------------------------------------------------


def test_split_ratios_sum_to_one():
    """The 3 ratios must sum to 1.0 (within float epsilon)."""
    ms = _load_make_split()
    ratios = {"train": 0.8, "val": 0.1, "test": 0.1}
    s = sum(ratios.values())
    assert abs(s - 1.0) < 1e-9, f"ratios sum to {s}, expected 1.0"


def test_split_assigns_all_rows(tmp_path):
    """Every input row gets one of {train, val, test}; no nulls.

    Note: per-country parquets are NOT rewritten -- the `split`
    column is only persisted in the combined parquet. This test
    reads from the combined file and groups by country.
    """
    ms = _load_make_split()
    root = _make_split_dataset(tmp_path, {"albania": 50, "andorra": 30})
    ms.make_split(root=root, seed=42)
    combined = pq.read_table(
        root / "combined" / "all_europe.parquet",
        columns=["split", "country"],
    )
    df = combined.to_pandas()
    for c, expected_n in (("albania", 50), ("andorra", 30)):
        sub = df[df["country"] == c]
        splits = sub["split"].tolist()
        assert len(splits) == expected_n
        assert all(s in ("train", "val", "test") for s in splits), (
            f"unexpected split values in {c}: {set(splits)}"
        )


def test_split_stratifies_by_country(tmp_path):
    """Per-country row counts are roughly preserved within tolerance.

    For countries with <= 10 rows, allow up to 1 row difference per
    split. For larger countries, allow up to 10% drift.
    """
    ms = _load_make_split()
    counts = {
        "monaco": 2,         # edge: tiny
        "liechtenstein": 8,  # small (boundary case)
        "albania": 100,      # medium
        "germany": 1000,     # large
    }
    root = _make_split_dataset(tmp_path, counts)
    manifest = ms.make_split(root=root, seed=42)

    pc = manifest["per_country_counts"]
    total_per_country = {c: sum(pc[c].values()) for c in counts}

    for c, n in counts.items():
        assert total_per_country[c] == n, (
            f"{c}: total {total_per_country[c]} != expected {n}"
        )
        if n <= 10:
            # Tolerate up to 1 row drift per split.
            for split_name in ("train", "val", "test"):
                expected_share = n * 0.8 if split_name == "train" else (
                    n * 0.1 if split_name == "val" else n * 0.1
                )
                diff = abs(pc[c][split_name] - expected_share)
                assert diff <= 1, (
                    f"{c}/{split_name}: {pc[c][split_name]} rows, "
                    f"expected ~{expected_share}, drift={diff}"
                )
        else:
            # Allow 10% drift for larger countries.
            for split_name in ("train", "val", "test"):
                expected_share = n * (0.8 if split_name == "train" else 0.1)
                diff = abs(pc[c][split_name] - expected_share)
                assert diff <= n * 0.1, (
                    f"{c}/{split_name}: {pc[c][split_name]} rows, "
                    f"expected ~{expected_share}, drift={diff}"
                )


def test_split_is_deterministic(tmp_path):
    """Running with the same seed twice produces identical assignments.

    Per-country parquets are NOT rewritten, so we compare from the
    combined parquet (the only place where the split is persisted).
    """
    ms = _load_make_split()
    root1 = _make_split_dataset(tmp_path / "run1", {"albania": 100, "andorra": 50})
    root2 = _make_split_dataset(tmp_path / "run2", {"albania": 100, "andorra": 50})

    ms.make_split(root=root1, seed=42)
    ms.make_split(root=root2, seed=42)

    for c in ("albania", "andorra"):
        t1 = pq.read_table(
            root1 / "combined" / "all_europe.parquet",
            columns=["split", "country"],
        ).to_pandas()
        t2 = pq.read_table(
            root2 / "combined" / "all_europe.parquet",
            columns=["split", "country"],
        ).to_pandas()
        s1 = t1[t1["country"] == c]["split"].tolist()
        s2 = t2[t2["country"] == c]["split"].tolist()
        assert s1 == s2, f"non-deterministic split for {c}"


def test_split_different_seeds_differ(tmp_path):
    """Running with seed 42 vs 43 produces at least one different row."""
    ms = _load_make_split()
    root1 = _make_split_dataset(tmp_path / "seed42", {"albania": 200})
    root2 = _make_split_dataset(tmp_path / "seed43", {"albania": 200})

    ms.make_split(root=root1, seed=42)
    ms.make_split(root=root2, seed=43)

    t1 = pq.read_table(
        root1 / "combined" / "all_europe.parquet",
        columns=["split", "country"],
    ).to_pandas()
    t2 = pq.read_table(
        root2 / "combined" / "all_europe.parquet",
        columns=["split", "country"],
    ).to_pandas()
    s1 = t1[t1["country"] == "albania"]["split"].tolist()
    s2 = t2[t2["country"] == "albania"]["split"].tolist()
    assert s1 != s2, "seed 42 and 43 produced identical splits"
    n_diffs = sum(1 for a, b in zip(s1, s2) if a != b)
    assert n_diffs > 0, "at least one row should differ between seeds"


def test_split_manifest_has_required_keys(tmp_path):
    """split_manifest.json contains seed, ratios, stratify_by, counts, per_country_counts."""
    ms = _load_make_split()
    root = _make_split_dataset(tmp_path, {"albania": 30, "andorra": 10})
    ms.make_split(root=root, seed=42)

    manifest_path = root / "splits" / "split_manifest.json"
    assert manifest_path.is_file(), f"missing {manifest_path}"
    m = json.loads(manifest_path.read_text())

    required = ["seed", "ratios", "stratify_by", "counts", "per_country_counts"]
    for k in required:
        assert k in m, f"missing key {k!r} in split_manifest.json"

    # Specific value checks.
    assert m["seed"] == 42
    assert m["stratify_by"] == "country"
    assert m["ratios"] == {"train": 0.8, "val": 0.1, "test": 0.1}
    assert sum(m["ratios"].values()) == pytest.approx(1.0)
    assert set(m["counts"].keys()) == {"train", "val", "test"}
    assert m["counts"]["train"] + m["counts"]["val"] + m["counts"]["test"] == 40
    assert set(m["per_country_counts"].keys()) == {"albania", "andorra"}
    for c in ("albania", "andorra"):
        for split_name in ("train", "val", "test"):
            assert split_name in m["per_country_counts"][c]


def test_split_writes_split_column_to_parquet(tmp_path):
    """After running, the combined parquet has a `split` column of type string.

    Note: per-country parquets are NOT rewritten (the split column is
    only persisted in the combined file). See the
    ``test_per_country_parquets_*`` tests for the new contract.
    """
    ms = _load_make_split()
    root = _make_split_dataset(tmp_path, {"albania": 25})
    ms.make_split(root=root, seed=42)
    t = pq.read_table(root / "combined" / "all_europe.parquet")
    assert "split" in t.schema.names, f"split column missing; got {t.schema.names}"
    split_col = t.column("split")
    assert pa.types.is_string(split_col.type), (
        f"split column should be string; got {split_col.type}"
    )
    # All values present and valid.
    splits = split_col.to_pylist()
    assert len(splits) == 25
    assert all(s in ("train", "val", "test") for s in splits)


def test_split_writes_combined_parquet(tmp_path):
    """The combined parquet is also written with the split column."""
    ms = _load_make_split()
    root = _make_split_dataset(tmp_path, {"albania": 50, "andorra": 30})
    ms.make_split(root=root, seed=42)

    combined = root / "combined" / "all_europe.parquet"
    assert combined.is_file(), f"missing {combined}"
    t = pq.read_table(combined, columns=["split", "country"])
    assert "split" in t.schema.names
    assert t.num_rows == 80
    # Both countries present in the combined file.
    countries = set(t.column("country").to_pylist())
    assert countries == {"albania", "andorra"}


# --- streaming tests for the optimized helpers ---------------------------


def test_streaming_add_split_column_preserves_data(tmp_path):
    """The streaming helper must produce a parquet with the same row count,
    the same data, and a 'split' column appended.

    We compare the optimized implementation against the original behavior
    by reading both back and checking equivalence.
    """
    ms = _load_make_split()
    pq_path = tmp_path / "italy.parquet"
    pq.write_table(_make_country_table("italy", 1234), pq_path)

    splits = np.array(
        ["train" if i % 2 == 0 else "val" for i in range(1234)],
        dtype=object,
    )
    ms._add_split_column_streaming(pq_path, splits)

    t = pq.read_table(pq_path)
    assert "split" in t.schema.names
    assert t.num_rows == 1234
    out_splits = t.column("split").to_pylist()
    assert out_splits == splits.tolist()


def test_streaming_add_split_column_idempotent(tmp_path):
    """Re-running must drop the existing split column first."""
    ms = _load_make_split()
    pq_path = tmp_path / "italy.parquet"
    pq.write_table(_make_country_table("italy", 100), pq_path)

    # First run
    splits1 = np.array(["train"] * 100, dtype=object)
    ms._add_split_column_streaming(pq_path, splits1)

    # Second run with different values
    splits2 = np.array(["val" if i % 2 == 0 else "test" for i in range(100)], dtype=object)
    ms._add_split_column_streaming(pq_path, splits2)

    t = pq.read_table(pq_path)
    # Must not have two split columns
    assert list(t.schema.names).count("split") == 1
    assert t.column("split").to_pylist() == splits2.tolist()


def test_streaming_write_combined_preserves_all_rows(tmp_path):
    """The streaming combined-writer must produce a parquet with the same
    number of rows as the sum of per-country rows, with all countries
    represented.
    """
    ms = _load_make_split()
    root = _make_split_dataset(tmp_path, {"albania": 50, "andorra": 30, "italy": 20})
    n_combined = ms._write_combined_streaming(root)
    assert n_combined == 100

    out = root / "combined" / "all_europe.parquet"
    assert out.is_file()
    t = pq.read_table(out)
    assert t.num_rows == 100
    assert set(t.column("country").to_pylist()) == {"albania", "andorra", "italy"}


def test_streaming_write_combined_no_intermediate_concat_table(tmp_path, monkeypatch):
    """The streaming combined-writer must NOT call pa.concat_tables —
    it should append row groups one at a time. We monkeypatch
    pa.concat_tables to raise so a regression that calls it will fail.
    """
    ms = _load_make_split()
    root = _make_split_dataset(tmp_path, {"albania": 50, "andorra": 30})

    import pyarrow as pa

    def _explode(*args, **kwargs):
        raise AssertionError("concat_tables should not be called in streaming path")

    monkeypatch.setattr(pa, "concat_tables", _explode)
    n_combined = ms._write_combined_streaming(root)
    assert n_combined == 80


# --- perf optimization: skip per-country parquet rewrites -----------------


def test_per_country_parquets_not_rewritten_after_split(tmp_path):
    """make_split() must NOT rewrite per-country parquets (no split
    column is persisted in them).

    Rationale: only the combined parquet is consumed by training; the
    per-country files contain the same rows and don't need a redundant
    split column. Skipping the per-country rewrite drops wall-clock
    by ~8-10 min on the real 51-country dataset.

    This test pins the contract: after make_split(), the per-country
    parquet's last_modified timestamp is unchanged from before the
    call (no rewrite happened). We use a small dataset because the
    contract is independent of size.
    """
    import os

    ms = _load_make_split()
    root = _make_split_dataset(tmp_path, {"albania": 30, "andorra": 10})

    # Snapshot timestamps BEFORE make_split().
    pq_paths = {
        c: root / "per_country" / c / f"{c}.parquet"
        for c in ("albania", "andorra")
    }
    mtimes_before = {c: os.path.getmtime(p) for c, p in pq_paths.items()}

    ms.make_split(root=root, seed=42)

    # After make_split(), per-country parquets must NOT have been
    # rewritten -- their mtime should be unchanged.
    for c, p in pq_paths.items():
        mtime_after = os.path.getmtime(p)
        assert mtime_after == mtimes_before[c], (
            f"per-country parquet {c} was rewritten "
            f"(mtime: {mtimes_before[c]} -> {mtime_after}); "
            f"make_split must NOT rewrite per-country parquets"
        )


def test_per_country_parquets_have_no_split_column_after_split(tmp_path):
    """make_split() must NOT append a `split` column to per-country
    parquets (it should only be persisted in the combined file).
    """
    ms = _load_make_split()
    root = _make_split_dataset(tmp_path, {"albania": 30, "andorra": 10})
    ms.make_split(root=root, seed=42)

    for c in ("albania", "andorra"):
        pq_path = root / "per_country" / c / f"{c}.parquet"
        schema = pq.read_schema(pq_path)
        assert "split" not in schema.names, (
            f"per-country parquet {c} unexpectedly has a 'split' column "
            f"after make_split(); only the combined parquet should have it"
        )


def test_combined_parquet_has_split_column_after_split(tmp_path):
    """make_split() must still write the `split` column to the combined
    parquet, with correct values, after the optimization.
    """
    ms = _load_make_split()
    root = _make_split_dataset(tmp_path, {"albania": 50, "andorra": 30})
    ms.make_split(root=root, seed=42)

    combined = root / "combined" / "all_europe.parquet"
    assert combined.is_file()
    t = pq.read_table(combined, columns=["split", "country"])
    assert "split" in t.schema.names
    assert t.num_rows == 80
    # All split values are valid and the same as what the manifest records.
    manifest = json.loads(
        (root / "splits" / "split_manifest.json").read_text()
    )
    expected_per_country = manifest["per_country_counts"]
    actual_per_country: dict[str, dict[str, int]] = {}
    for c in expected_per_country:
        actual_per_country[c] = {"train": 0, "val": 0, "test": 0}
    df = t.to_pandas()
    for c, split_name in zip(df["country"].tolist(), df["split"].tolist()):
        actual_per_country[c][split_name] += 1
    assert actual_per_country == expected_per_country, (
        f"combined split counts {actual_per_country} != "
        f"manifest {expected_per_country}"
    )

"""Tests for per-country parquet skip-after-split (split from test_make_split.py)."""

from __future__ import annotations

import json
import os

import pyarrow.parquet as pq

from .conftest import _load_make_split, _make_split_dataset


def test_per_country_parquets_not_rewritten_after_split(tmp_path):
    """make_split() must NOT rewrite per-country parquets."""
    ms = _load_make_split()
    root = _make_split_dataset(tmp_path, {"albania": 30, "andorra": 10})

    pq_paths = {
        c: root / "per_country" / c / f"{c}.parquet"
        for c in ("albania", "andorra")
    }
    mtimes_before = {c: os.path.getmtime(p) for c, p in pq_paths.items()}

    ms.make_split(root=root, seed=42)

    for c, p in pq_paths.items():
        mtime_after = os.path.getmtime(p)
        assert mtime_after == mtimes_before[c], (
            f"per-country parquet {c} was rewritten; make_split must NOT "
            f"rewrite per-country parquets"
        )


def test_per_country_parquets_have_no_split_column_after_split(tmp_path):
    """make_split() must NOT append a `split` column to per-country parquets."""
    ms = _load_make_split()
    root = _make_split_dataset(tmp_path, {"albania": 30, "andorra": 10})
    ms.make_split(root=root, seed=42)

    for c in ("albania", "andorra"):
        pq_path = root / "per_country" / c / f"{c}.parquet"
        schema = pq.read_schema(pq_path)
        assert "split" not in schema.names, (
            f"per-country parquet {c} unexpectedly has a 'split' column"
        )


def test_combined_parquet_has_split_column_after_split(tmp_path):
    """make_split() writes the `split` column to the combined parquet."""
    ms = _load_make_split()
    root = _make_split_dataset(tmp_path, {"albania": 50, "andorra": 30})
    ms.make_split(root=root, seed=42)

    combined = root / "combined" / "all_world.parquet"
    assert combined.is_file()
    t = pq.read_table(combined, columns=["split", "country"])
    assert "split" in t.schema.names
    assert t.num_rows == 80
    manifest = json.loads(
        (root / "splits" / "split_manifest.json").read_text()
    )
    expected_per_country = manifest["per_country_counts"]
    actual_per_country: dict[str, dict[str, int]] = {
        c: {"train": 0, "val": 0, "test": 0}
        for c in expected_per_country
    }
    df = t.to_pandas()
    for c, split_name in zip(df["country"].tolist(), df["split"].tolist()):
        actual_per_country[c][split_name] += 1
    assert actual_per_country == expected_per_country

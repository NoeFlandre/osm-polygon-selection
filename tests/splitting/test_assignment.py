"""Tests for per-country split assignment (split from test_make_split.py)."""

from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq
import pytest

from .conftest import _load_make_split, _make_split_dataset


def test_split_ratios_sum_to_one():
    """The 3 ratios must sum to 1.0 (within float epsilon)."""
    ms = _load_make_split()
    ratios = {"train": 0.8, "val": 0.1, "test": 0.1}
    s = sum(ratios.values())
    assert abs(s - 1.0) < 1e-9, f"ratios sum to {s}, expected 1.0"


def test_split_assigns_all_rows(tmp_path):
    """Every input row gets one of {train, val, test}; no nulls."""
    ms = _load_make_split()
    root = _make_split_dataset(tmp_path, {"albania": 50, "andorra": 30})
    ms.make_split(root=root, seed=42)
    combined = pq.read_table(
        root / "combined" / "all_world.parquet",
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
    """Per-country row counts are roughly preserved within tolerance."""
    ms = _load_make_split()
    counts = {
        "monaco": 2,
        "liechtenstein": 8,
        "albania": 100,
        "germany": 1000,
    }
    root = _make_split_dataset(tmp_path, counts)
    manifest = ms.make_split(root=root, seed=42)

    pc = manifest["per_country_counts"]
    total_per_country = {c: sum(pc[c].values()) for c in counts}

    for c, n in counts.items():
        assert total_per_country[c] == n
        if n <= 10:
            for split_name in ("train", "val", "test"):
                expected_share = n * (0.8 if split_name == "train" else 0.1)
                diff = abs(pc[c][split_name] - expected_share)
                assert diff <= 1
        else:
            for split_name in ("train", "val", "test"):
                expected_share = n * (0.8 if split_name == "train" else 0.1)
                diff = abs(pc[c][split_name] - expected_share)
                assert diff <= n * 0.1


def test_split_is_deterministic(tmp_path):
    """Same seed twice produces identical assignments."""
    ms = _load_make_split()
    root1 = _make_split_dataset(tmp_path / "run1", {"albania": 100, "andorra": 50})
    root2 = _make_split_dataset(tmp_path / "run2", {"albania": 100, "andorra": 50})

    ms.make_split(root=root1, seed=42)
    ms.make_split(root=root2, seed=42)

    for c in ("albania", "andorra"):
        t1 = pq.read_table(
            root1 / "combined" / "all_world.parquet",
            columns=["split", "country"],
        ).to_pandas()
        t2 = pq.read_table(
            root2 / "combined" / "all_world.parquet",
            columns=["split", "country"],
        ).to_pandas()
        s1 = t1[t1["country"] == c]["split"].tolist()
        s2 = t2[t2["country"] == c]["split"].tolist()
        assert s1 == s2, f"non-deterministic split for {c}"


def test_split_different_seeds_differ(tmp_path):
    """Seed 42 vs 43 produces at least one different row."""
    ms = _load_make_split()
    root1 = _make_split_dataset(tmp_path / "seed42", {"albania": 200})
    root2 = _make_split_dataset(tmp_path / "seed43", {"albania": 200})

    ms.make_split(root=root1, seed=42)
    ms.make_split(root=root2, seed=43)

    t1 = pq.read_table(
        root1 / "combined" / "all_world.parquet",
        columns=["split", "country"],
    ).to_pandas()
    t2 = pq.read_table(
        root2 / "combined" / "all_world.parquet",
        columns=["split", "country"],
    ).to_pandas()
    s1 = t1[t1["country"] == "albania"]["split"].tolist()
    s2 = t2[t2["country"] == "albania"]["split"].tolist()
    assert s1 != s2
    n_diffs = sum(1 for a, b in zip(s1, s2) if a != b)
    assert n_diffs > 0

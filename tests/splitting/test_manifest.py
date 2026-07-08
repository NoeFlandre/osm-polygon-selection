"""Tests for split_manifest.json shape (split from test_make_split.py)."""

from __future__ import annotations

import json

import pytest

from .conftest import _load_make_split, _make_split_dataset


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

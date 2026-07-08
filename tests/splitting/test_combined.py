"""Tests for combined-parquet writer (split from test_make_split.py)."""

from __future__ import annotations

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from .conftest import _load_make_split, _make_country_table, _make_split_dataset


def test_split_writes_split_column_to_parquet(tmp_path):
    """After running, the combined parquet has a `split` column of type string."""
    ms = _load_make_split()
    root = _make_split_dataset(tmp_path, {"albania": 25})
    ms.make_split(root=root, seed=42)
    t = pq.read_table(root / "combined" / "all_world.parquet")
    assert "split" in t.schema.names
    split_col = t.column("split")
    assert pa.types.is_string(split_col.type)
    splits = split_col.to_pylist()
    assert len(splits) == 25
    assert all(s in ("train", "val", "test") for s in splits)


def test_split_writes_combined_parquet(tmp_path):
    """The combined parquet is also written with the split column."""
    ms = _load_make_split()
    root = _make_split_dataset(tmp_path, {"albania": 50, "andorra": 30})
    ms.make_split(root=root, seed=42)

    combined = root / "combined" / "all_world.parquet"
    assert combined.is_file()
    t = pq.read_table(combined, columns=["split", "country"])
    assert "split" in t.schema.names
    assert t.num_rows == 80
    countries = set(t.column("country").to_pylist())
    assert countries == {"albania", "andorra"}


def test_streaming_add_split_column_preserves_data(tmp_path):
    """Streaming helper preserves row count, data, and split column."""
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
    assert t.column("split").to_pylist() == splits.tolist()


def test_streaming_add_split_column_idempotent(tmp_path):
    """Re-running drops the existing split column first."""
    ms = _load_make_split()
    pq_path = tmp_path / "italy.parquet"
    pq.write_table(_make_country_table("italy", 100), pq_path)

    splits1 = np.array(["train"] * 100, dtype=object)
    ms._add_split_column_streaming(pq_path, splits1)

    splits2 = np.array(["val" if i % 2 == 0 else "test" for i in range(100)], dtype=object)
    ms._add_split_column_streaming(pq_path, splits2)

    t = pq.read_table(pq_path)
    assert list(t.schema.names).count("split") == 1
    assert t.column("split").to_pylist() == splits2.tolist()


def test_streaming_write_combined_preserves_all_rows(tmp_path):
    """Streaming combined-writer preserves row count + country coverage."""
    ms = _load_make_split()
    root = _make_split_dataset(tmp_path, {"albania": 50, "andorra": 30, "italy": 20})
    n_combined = ms._write_combined_streaming(root)
    assert n_combined == 100

    out = root / "combined" / "all_world.parquet"
    assert out.is_file()
    t = pq.read_table(out)
    assert t.num_rows == 100
    assert set(t.column("country").to_pylist()) == {"albania", "andorra", "italy"}


def test_streaming_write_combined_no_intermediate_concat_table(tmp_path, monkeypatch):
    """Streaming combined-writer must NOT call pa.concat_tables."""
    ms = _load_make_split()
    root = _make_split_dataset(tmp_path, {"albania": 50, "andorra": 30})

    import pyarrow as pa

    def _explode(*args, **kwargs):
        raise AssertionError("concat_tables should not be called in streaming path")

    monkeypatch.setattr(pa, "concat_tables", _explode)
    n_combined = ms._write_combined_streaming(root)
    assert n_combined == 80

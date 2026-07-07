"""Tests for `osm_polygon_selection.dataset_build.split_parquets.write_split_parquets`.

These pin the contract used by `scripts/split_parquets.py`:

- One parquet per split is written under `out_dir` (train.parquet,
  val.parquet, test.parquet).
- Each per-split file contains exactly the rows whose `split` column
  matches that split.
- The output schema does NOT contain a `split` column (it is dropped
  since it is uniform within each per-split file).
- A dict of counts is returned.
- If the source parquet is missing, a clear error is raised.
"""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from osm_polygon_selection.dataset_build.split_parquets import write_split_parquets


def _make_source(tmp_path: Path) -> Path:
    """Write a tiny parquet with a `split` column (train/val/test mix)."""
    table = pa.table(
        {
            "country": ["a", "b", "c", "d", "e"],
            "centroid_lon": [0.0, 1.0, 2.0, 3.0, 4.0],
            "centroid_lat": [0.0, 1.0, 2.0, 3.0, 4.0],
            "area_km2": [1.0, 2.0, 3.0, 4.0, 5.0],
            "split": ["train", "val", "test", "train", "val"],
        }
    )
    source = tmp_path / "source.parquet"
    pq.write_table(table, source)
    return source


def test_writes_one_parquet_per_split(tmp_path: Path) -> None:
    source = _make_source(tmp_path)
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    counts = write_split_parquets(source, out_dir)

    assert (out_dir / "train.parquet").is_file()
    assert (out_dir / "val.parquet").is_file()
    assert (out_dir / "test.parquet").is_file()


def test_returns_correct_row_counts(tmp_path: Path) -> None:
    source = _make_source(tmp_path)
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    counts = write_split_parquets(source, out_dir)

    # From _make_source: 2 train, 2 val, 1 test.
    assert counts == {"train": 2, "val": 2, "test": 1}


def test_output_schemas_lack_split_column(tmp_path: Path) -> None:
    source = _make_source(tmp_path)
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    write_split_parquets(source, out_dir)

    for split in ("train", "val", "test"):
        schema = pq.read_schema(out_dir / f"{split}.parquet")
        assert "split" not in schema.names, (
            f"{split}.parquet schema still has 'split' column: {schema.names}"
        )


def test_output_schemas_retain_other_columns(tmp_path: Path) -> None:
    source = _make_source(tmp_path)
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    write_split_parquets(source, out_dir)

    expected = {"country", "centroid_lon", "centroid_lat", "area_km2"}
    for split in ("train", "val", "test"):
        schema = pq.read_schema(out_dir / f"{split}.parquet")
        assert expected.issubset(set(schema.names)), (
            f"{split}.parquet missing columns: {expected - set(schema.names)}"
        )


def test_output_row_counts_match_source(tmp_path: Path) -> None:
    source = _make_source(tmp_path)
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    counts = write_split_parquets(source, out_dir)

    src = pq.read_table(source)
    assert sum(counts.values()) == src.num_rows


def test_missing_source_raises(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    missing = tmp_path / "no-such-file.parquet"

    with pytest.raises(FileNotFoundError):
        write_split_parquets(missing, out_dir)


def test_writers_closed_on_exception(tmp_path: Path, monkeypatch) -> None:
    """Regression: writers must be closed even when row-group processing fails.

    We monkey-patch pq.ParquetFile.read_row_group to raise after the
    first call. The function should propagate the exception AND have
    closed every opened writer.
    """
    import pyarrow.parquet as pq

    source = _make_source(tmp_path)
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    original_writer_init = pq.ParquetWriter.__init__
    original_writer_close = pq.ParquetWriter.close

    close_calls: list[str] = []

    def tracking_close(self):  # type: ignore[no-untyped-def]
        close_calls.append("close")
        return original_writer_close(self)

    def boom_init(self, path, schema, **kwargs):  # type: ignore[no-untyped-def]
        # Allow normal initialization.
        return original_writer_init(self, path, schema, **kwargs)

    def boom_read_row_group(self, idx):  # type: ignore[no-untyped-def]
        raise RuntimeError("simulated mid-loop failure")

    monkeypatch.setattr(pq.ParquetWriter, "__init__", boom_init)
    monkeypatch.setattr(pq.ParquetWriter, "close", tracking_close)
    monkeypatch.setattr(
        pq.ParquetFile, "read_row_group", boom_read_row_group
    )

    with pytest.raises(RuntimeError, match="simulated mid-loop failure"):
        write_split_parquets(source, out_dir)

    # All 3 writers (train/val/test) must have been closed.
    assert len(close_calls) == 3, (
        f"expected 3 close() calls (one per writer); got {len(close_calls)}"
    )

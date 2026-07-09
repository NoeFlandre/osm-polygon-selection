"""Tests for the atomic write helpers."""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from osm_polygon_selection.parquet_write.atomic import (
    atomic_write_empty_parquet,
    atomic_write_parquet,
)
from osm_polygon_selection.schema_defs import build_schema


class TestAtomicWriteParquet:
    def test_atomic_write_creates_final_file(self, tmp_path: Path) -> None:
        final = tmp_path / "out.parquet"
        def _writer(tmp: Path) -> None:
            table = pa.table({"x": [1, 2, 3]})
            pq.write_table(table, tmp)
        atomic_write_parquet(final, _writer, prefix=".build_")
        assert final.is_file()
        # No stray temp files remain.
        assert list(tmp_path.glob(".build_*")) == []

    def test_atomic_write_replaces_existing(self, tmp_path: Path) -> None:
        final = tmp_path / "out.parquet"
        final.write_text("placeholder")
        def _writer(tmp: Path) -> None:
            table = pa.table({"y": [42]})
            pq.write_table(table, tmp)
        atomic_write_parquet(final, _writer, prefix=".build_")
        t = pq.read_table(final)
        assert t.column("y").to_pylist() == [42]

    def test_atomic_write_empty_parquet(self, tmp_path: Path) -> None:
        final = tmp_path / "empty.parquet"
        schema = build_schema(geometry_encoding="wkt")
        atomic_write_empty_parquet(final, schema)
        assert final.is_file()
        # Empty parquet has 0 rows but the schema is preserved.
        t = pq.read_table(final)
        assert t.num_rows == 0
        assert "osm_id" in t.schema.names

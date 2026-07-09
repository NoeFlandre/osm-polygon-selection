"""Tests for parquet compression settings."""

from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq

from osm_polygon_selection.streaming_writer import write_jsonl_to_parquet

from .conftest import _row, _write_jsonl


class TestCompression:
    def test_default_compression_is_zstd(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "in.jsonl"
        out = tmp_path / "out.parquet"
        _write_jsonl(jsonl, [_row(i) for i in range(1, 101)])
        write_jsonl_to_parquet(
            jsonl_path=jsonl,
            parquet_path=out,
            country="italy",
            extract_status="clean",
            pbf_date="2026-06-26",
        )
        meta = pq.read_metadata(out)
        codec = meta.row_group(0).column(0).compression
        assert codec in ("ZSTD", "zstd"), f"expected zstd, got {codec}"

    def test_explicit_compression_override(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "in.jsonl"
        out = tmp_path / "out.parquet"
        _write_jsonl(jsonl, [_row(i) for i in range(1, 101)])
        write_jsonl_to_parquet(
            jsonl_path=jsonl,
            parquet_path=out,
            country="italy",
            extract_status="clean",
            pbf_date="2026-06-26",
            compression="snappy",
        )
        meta = pq.read_metadata(out)
        assert meta.row_group(0).column(0).compression in ("SNAPPY", "snappy")

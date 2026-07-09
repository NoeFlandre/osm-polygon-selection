"""Tests for matched_tag backfill."""

from __future__ import annotations

import json
from pathlib import Path

import pyarrow.parquet as pq

from osm_polygon_selection.streaming_writer import write_jsonl_to_parquet

from .conftest import _row, _write_jsonl


def _write_whitelist(path: Path, tags: list[str]) -> None:
    path.write_text(json.dumps(tags))


class TestMatchedTagBackfill:
    def test_backfilled_when_missing(self, tmp_path: Path) -> None:
        """Legacy 03_classified.jsonl files don't have matched_tag.
        The streaming writer must compute it from row.tags against
        the whitelist (vectorized)."""
        wl = tmp_path / "whitelist.json"
        _write_whitelist(wl, ["natural=water"])
        jsonl = tmp_path / "in.jsonl"
        out = tmp_path / "out.parquet"
        _write_jsonl(jsonl, [
            _row(1, tags=["name=Lake", "natural=water"]),
            _row(2, tags=["place=islet"]),
        ])
        write_jsonl_to_parquet(
            jsonl_path=jsonl,
            parquet_path=out,
            country="italy",
            extract_status="clean",
            pbf_date="2026-06-26",
            whitelist_path=wl,
        )
        t = pq.read_table(out)
        assert t.column("matched_tag").to_pylist() == ["natural=water", ""]

    def test_passthrough_when_set(self, tmp_path: Path) -> None:
        """matched_tag is pre-set; the writer must NOT overwrite it."""
        wl = tmp_path / "whitelist.json"
        _write_whitelist(wl, ["natural=water"])
        jsonl = tmp_path / "in.jsonl"
        out = tmp_path / "out.parquet"
        _write_jsonl(jsonl, [
            _row(1, tags=["name=Lake"], matched_tag="landuse=forest"),
        ])
        write_jsonl_to_parquet(
            jsonl_path=jsonl,
            parquet_path=out,
            country="italy",
            extract_status="clean",
            pbf_date="2026-06-26",
            whitelist_path=wl,
        )
        t = pq.read_table(out)
        assert t.column("matched_tag").to_pylist() == ["landuse=forest"]

    def test_no_whitelist_skips_backfill(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "in.jsonl"
        out = tmp_path / "out.parquet"
        _write_jsonl(jsonl, [_row(1, tags=["natural=water"], matched_tag="")])
        write_jsonl_to_parquet(
            jsonl_path=jsonl,
            parquet_path=out,
            country="italy",
            extract_status="clean",
            pbf_date="2026-06-26",
            # no whitelist_path
        )
        t = pq.read_table(out)
        # matched_tag stays empty (no backfill path was taken).
        assert t.column("matched_tag").to_pylist() == [""]

"""Tests for the full-row example table renderer."""

from __future__ import annotations

from pathlib import Path

from osm_polygon_selection.sample_tables import build_example_row_table

from .conftest import _write_jsonl


class TestBuildExampleRowTable:
    def test_returns_message_for_missing_sample(self, tmp_path: Path) -> None:
        out = build_example_row_table(tmp_path / "missing.jsonl")
        assert "no sample row available" in out

    def test_renders_all_columns(self, tmp_path: Path) -> None:
        sample = tmp_path / "sample.jsonl"
        _write_jsonl(sample, [{"country": "italy", "osm_id": 1, "size_bin": "small"}])
        out = build_example_row_table(sample, fallback_dir=tmp_path)
        assert "| column | value |" in out
        assert "osm_id" in out
        assert "size_bin" in out
        assert "country" in out
        assert "geometry_wkt" in out

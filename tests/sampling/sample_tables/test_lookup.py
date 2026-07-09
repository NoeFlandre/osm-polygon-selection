"""Tests for sample-row picker + per-country parquet lookup."""

from __future__ import annotations

from pathlib import Path

from osm_polygon_selection.sample_tables import (
    fetch_full_row_from_parquet,
    pick_sample_row,
)

from .conftest import _write_jsonl, _write_parquet


class TestPickSampleRow:
    def test_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        assert pick_sample_row(tmp_path / "missing.jsonl") is None

    def test_picks_preferred_country_and_tag(self, tmp_path: Path) -> None:
        sample = tmp_path / "sample.jsonl"
        _write_jsonl(sample, [
            {"country": "italy", "matched_tag": "natural=water", "osm_id": 1},
            {"country": "liechtenstein", "matched_tag": "landuse=farmland", "osm_id": 2},
            {"country": "liechtenstein", "matched_tag": "natural=water", "osm_id": 3},
        ])
        row = pick_sample_row(
            sample, prefer_country="liechtenstein", prefer_tag_prefix="natural="
        )
        assert row is not None
        assert row["osm_id"] == 3

    def test_falls_back_to_country(self, tmp_path: Path) -> None:
        sample = tmp_path / "sample.jsonl"
        _write_jsonl(sample, [
            {"country": "italy", "osm_id": 1},
            {"country": "liechtenstein", "osm_id": 2},
        ])
        row = pick_sample_row(sample, prefer_country="liechtenstein")
        assert row["osm_id"] == 2

    def test_falls_back_to_first_row(self, tmp_path: Path) -> None:
        sample = tmp_path / "sample.jsonl"
        _write_jsonl(sample, [{"country": "italy", "osm_id": 1}])
        row = pick_sample_row(sample, prefer_country="liechtenstein")
        assert row["osm_id"] == 1


class TestFetchFullRowFromParquet:
    def test_returns_none_for_missing_parquet(self, tmp_path: Path) -> None:
        assert fetch_full_row_from_parquet(tmp_path / "missing", 1) is None

    def test_returns_none_for_missing_osm_id(self, tmp_path: Path) -> None:
        pq_path = tmp_path / "liechtenstein" / "liechtenstein.parquet"
        _write_parquet(pq_path, [{"osm_id": 99, "name": "x"}])
        assert fetch_full_row_from_parquet(pq_path, 1) is None

    def test_returns_full_row(self, tmp_path: Path) -> None:
        pq_path = tmp_path / "liechtenstein" / "liechtenstein.parquet"
        _write_parquet(pq_path, [
            {"osm_id": 1, "name": "x", "tags": ["natural=water"]},
            {"osm_id": 2, "name": "y", "tags": ["landuse=farmland"]},
        ])
        result = fetch_full_row_from_parquet(pq_path, 2)
        assert result is not None
        assert result["name"] == "y"
        assert result["tags"] == ["landuse=farmland"]

"""Tests for osm_polygon_selection.sample_table.

TDD red phase: written before src/osm_polygon_selection/sample_table.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from osm_polygon_selection.sample_table import (
    SIZE_BIN_ORDER,
    build_example_row_table,
    build_size_bin_distribution_table,
    compute_sample_size_bin_distribution,
    fetch_full_row_from_parquet,
    pick_sample_row,
    truncate,
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def _write_parquet(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows), path)


class TestSizeBinOrder:
    def test_order_is_small_medium_large(self) -> None:
        assert SIZE_BIN_ORDER == ("small", "medium", "large")


class TestComputeDistribution:
    def test_returns_list_of_tuples_in_order(self, tmp_path: Path) -> None:
        sample = tmp_path / "sample.jsonl"
        _write_jsonl(sample, [
            {"size_bin": "small"},
            {"size_bin": "small"},
            {"size_bin": "medium"},
            {"size_bin": "large"},
        ])
        dist = compute_sample_size_bin_distribution(sample)
        assert dist == [
            ("small", 2, 50.0),
            ("medium", 1, 25.0),
            ("large", 1, 25.0),
        ]

    def test_empty_input_returns_zeros(self, tmp_path: Path) -> None:
        sample = tmp_path / "empty.jsonl"
        sample.write_text("")
        dist = compute_sample_size_bin_distribution(sample)
        assert dist == [("small", 0, 0.0), ("medium", 0, 0.0), ("large", 0, 0.0)]

    def test_missing_size_bin_counts_as_empty(self, tmp_path: Path) -> None:
        sample = tmp_path / "missing.jsonl"
        _write_jsonl(sample, [{"foo": "bar"}])
        dist = compute_sample_size_bin_distribution(sample)
        assert dist[0] == ("small", 0, 0.0)


class TestBuildDistributionTable:
    def test_renders_markdown_table(self) -> None:
        dist = [("small", 100, 80.0), ("medium", 20, 16.0), ("large", 5, 4.0)]
        out = build_size_bin_distribution_table(dist)
        assert "| size_bin | count | pct |" in out
        assert "| small | 100 | 80.0% |" in out
        assert "**Total**" in out
        assert "| **Total** | 125 | 100.0% |" in out


class TestTruncate:
    def test_short_string_unchanged(self) -> None:
        assert truncate("hello") == "hello"

    def test_long_string_truncated_with_ellipsis(self) -> None:
        out = truncate("x" * 200, max_len=50)
        assert len(out) == 50
        assert out.endswith("...")

    def test_exact_length_unchanged(self) -> None:
        assert truncate("x" * 10, max_len=10) == "x" * 10

    def test_none_returns_empty(self) -> None:
        assert truncate(None) == ""


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

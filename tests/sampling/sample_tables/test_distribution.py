"""Tests for size-bin distribution (sample + global)."""

from __future__ import annotations

from pathlib import Path

from osm_polygon_selection.sample_tables import (
    SIZE_BIN_ORDER,
    compute_global_size_bin_distribution,
    compute_sample_size_bin_distribution,
)

from .conftest import _write_jsonl, _write_parquet


class TestSizeBinOrder:
    def test_order_is_small_medium_large(self) -> None:
        assert SIZE_BIN_ORDER == ("small", "medium", "large")


class TestSampleDistribution:
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


class TestGlobalDistribution:
    """The "global" distribution is computed from the FULL dataset,
    not from a sample. Implemented via pyarrow.compute.value_counts
    against a per-country parquet (or combined all_world.parquet).
    """

    def test_returns_zero_for_missing_combined(self, tmp_path: Path) -> None:
        dist = compute_global_size_bin_distribution(tmp_path)
        assert dist == [("small", 0, 0.0), ("medium", 0, 0.0), ("large", 0, 0.0)]

    def test_aggregates_per_country(self, tmp_path: Path) -> None:
        layout = tmp_path
        for sub in ("per_country", "combined"):
            (layout / sub).mkdir(exist_ok=True)
        _write_parquet(
            layout / "per_country" / "a" / "a.parquet",
            [
                {"osm_id": 1, "size_bin": "small"},
                {"osm_id": 2, "size_bin": "small"},
                {"osm_id": 3, "size_bin": "medium"},
            ],
        )
        _write_parquet(
            layout / "per_country" / "b" / "b.parquet",
            [
                {"osm_id": 1, "size_bin": "small"},
                {"osm_id": 2, "size_bin": "large"},
            ],
        )
        dist = compute_global_size_bin_distribution(layout)
        assert dist == [
            ("small", 3, 60.0),
            ("medium", 1, 20.0),
            ("large", 1, 20.0),
        ]

    def test_prefers_combined_over_per_country(self, tmp_path: Path) -> None:
        """If combined/all_world.parquet exists, use it (NOT per_country)."""
        layout = tmp_path
        for sub in ("per_country", "combined"):
            (layout / sub).mkdir(exist_ok=True)
        _write_parquet(
            layout / "per_country" / "a" / "a.parquet",
            [
                {"osm_id": 1, "size_bin": "small"},
                {"osm_id": 2, "size_bin": "medium"},
            ],
        )
        _write_parquet(
            layout / "combined" / "all_world.parquet",
            [
                {"osm_id": 1, "size_bin": "small"},
                {"osm_id": 2, "size_bin": "small"},
                {"osm_id": 3, "size_bin": "large"},
            ],
        )
        dist = compute_global_size_bin_distribution(layout)
        assert dist == [
            ("small", 2, 66.7),
            ("medium", 0, 0.0),
            ("large", 1, 33.3),
        ]

    def test_skips_per_country_with_no_size_bin_column(self, tmp_path: Path) -> None:
        """Per-country parquets may have older schemas without size_bin.
        Skip them gracefully (don't crash)."""
        layout = tmp_path
        (layout / "per_country").mkdir(exist_ok=True)
        _write_parquet(
            layout / "per_country" / "a" / "a.parquet",
            [{"osm_id": 1, "name": "no_size_bin"}],
        )
        dist = compute_global_size_bin_distribution(layout)
        assert dist == [("small", 0, 0.0), ("medium", 0, 0.0), ("large", 0, 0.0)]

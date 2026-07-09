"""Tests for markdown formatting helpers."""

from __future__ import annotations

from osm_polygon_selection.sample_tables import (
    build_size_bin_distribution_table,
    truncate,
)


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


class TestBuildDistributionTable:
    def test_renders_markdown_table(self) -> None:
        dist = [("small", 100, 80.0), ("medium", 20, 16.0), ("large", 5, 4.0)]
        out = build_size_bin_distribution_table(dist)
        assert "| size_bin | count | pct |" in out
        assert "| small | 100 | 80.0% |" in out
        assert "**Total**" in out
        assert "| **Total** | 125 | 100.0% |" in out

    def test_global_counts_format_correctly(self) -> None:
        dist = [
            ("small", 5_836_893, 79.9),
            ("medium", 1_292_136, 17.7),
            ("large", 173_753, 2.4),
        ]
        out = build_size_bin_distribution_table(dist)
        assert "| small | 5,836,893 | 79.9% |" in out
        assert "| medium | 1,292,136 | 17.7% |" in out
        assert "| large | 173,753 | 2.4% |" in out
        assert "| **Total** | 7,302,782 |" in out

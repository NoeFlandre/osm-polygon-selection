"""Tests for TestBuildRootReadme in osm_polygon_selection.readme_render.

Split from test_render.py during the quality-uplift-public-hardening phase.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from .conftest import _country, _manifest
from osm_polygon_selection.readme_render import build_root_readme

class TestBuildRootReadme:
    def test_has_yaml_frontmatter(self, tmp_path: Path) -> None:
        sample = tmp_path / "sample.jsonl"
        sample.write_text("")
        out = build_root_readme(_manifest([_country("albania", 100)]), tmp_path)
        assert out.startswith("---\n")
        assert "license: odbl" in out
        assert "task_categories:" in out

    def test_mentions_country_count(self, tmp_path: Path) -> None:
        sample = tmp_path / "sample.jsonl"
        sample.write_text("")
        out = build_root_readme(
            _manifest([_country("a", 1), _country("b", 2), _country("c", 3)]),
            tmp_path,
        )
        assert "from **3 countries**" in out
        # The intro is country-count-only; no hardcoded "European"
        # or "Africa" strings should appear (those would couple the
        # README to the current continent mix and drift over time).
        assert "European" not in out
        assert "in Africa" not in out

    def test_mentions_total_polygons(self, tmp_path: Path) -> None:
        sample = tmp_path / "sample.jsonl"
        sample.write_text("")
        out = build_root_readme(_manifest([_country("a", 100)]), tmp_path)
        assert "100" in out

    def test_includes_size_bin_distribution(self, tmp_path: Path) -> None:
        sample = tmp_path / "sample.jsonl"
        sample.write_text('{"size_bin": "small"}\n{"size_bin": "large"}\n')
        # Build a fake combined parquet so the GLOBAL distribution
        # function returns real counts (which is what the README
        # should be displaying now, not sample-only).
        (tmp_path / "combined").mkdir(exist_ok=True)
        import pyarrow as pa
        import pyarrow.parquet as pq
        pq.write_table(
            pa.Table.from_pylist([
                {"osm_id": 1, "size_bin": "small"},
                {"osm_id": 2, "size_bin": "small"},
                {"osm_id": 3, "size_bin": "large"},
            ]),
            tmp_path / "combined" / "all_world.parquet",
        )
        out = build_root_readme(_manifest([_country("a", 3)]), tmp_path)
        assert "Size-bin distribution" in out
        assert "| small |" in out
        assert "| large |" in out
        assert "| **Total** | 3,000" in out or "| **Total** | 3 |" in out

    def test_distribution_is_global_not_sample(self, tmp_path: Path) -> None:
        """The README must show GLOBAL counts (from combined parquet),
        NOT the sample JSONL counts. The sample has 1 small + 1 large.
        The combined has 100 small + 50 medium + 10 large. The README
        must reflect the combined totals, not the sample.
        """
        sample = tmp_path / "sample" / "sample_map.jsonl"
        sample.parent.mkdir(parents=True, exist_ok=True)
        sample.write_text('{"size_bin": "small"}\n{"size_bin": "large"}\n')
        (tmp_path / "combined").mkdir(exist_ok=True)
        import pyarrow as pa
        import pyarrow.parquet as pq
        rows = [{"osm_id": i, "size_bin": "small"} for i in range(100)]
        rows += [{"osm_id": i, "size_bin": "medium"} for i in range(50)]
        rows += [{"osm_id": i, "size_bin": "large"} for i in range(10)]
        pq.write_table(pa.Table.from_pylist(rows),
                       tmp_path / "combined" / "all_world.parquet")
        out = build_root_readme(_manifest([_country("a", 160)]), tmp_path)
        # Global totals must appear (with thousands-separator formatting).
        assert "| small | 100 |" in out
        assert "| medium | 50 |" in out
        assert "| large | 10 |" in out
        # Section header must say "full dataset", not "Sample"
        assert "Size-bin distribution (full dataset)" in out
        assert "Sample size-bin distribution" not in out
        # And the table total (sum of all bins = 160) must appear.
        assert "| **Total** | 160 |" in out

    def test_includes_example_row_section(self, tmp_path: Path) -> None:
        sample = tmp_path / "sample.jsonl"
        sample.write_text('{"country": "italy", "osm_id": 1, "size_bin": "small"}\n')
        out = build_root_readme(_manifest([_country("italy", 1)]), tmp_path)
        assert "Example row" in out

    def test_includes_train_val_test_section_when_manifest_present(
        self, tmp_path: Path,
    ) -> None:
        sample = tmp_path / "sample.jsonl"
        sample.write_text("")
        splits = tmp_path / "splits" / "split_manifest.json"
        splits.parent.mkdir(parents=True, exist_ok=True)
        splits.write_text(json.dumps({
            "seed": 42,
            "ratios": {"train": 0.8, "val": 0.1, "test": 0.1},
            "stratify_by": "country",
            "counts": {"train": 100, "val": 10, "test": 10},
            "per_country_counts": {},
        }))
        out = build_root_readme(_manifest([_country("a", 120)]), tmp_path)
        assert "Train / val / test split" in out
        assert "5,841,700" in out or "**Total**" in out

    def test_no_split_section_when_no_manifest(self, tmp_path: Path) -> None:
        sample = tmp_path / "sample.jsonl"
        sample.write_text("")
        out = build_root_readme(_manifest([_country("a", 1)]), tmp_path)
        # Should not crash; should still render
        assert "A curated set" in out



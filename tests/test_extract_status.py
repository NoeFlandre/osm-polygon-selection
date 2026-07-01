"""Tests for osm_polygon_selection.extract_status.

TDD red phase: written before src/osm_polygon_selection/extract_status.py.
"""

from __future__ import annotations

from pathlib import Path

from osm_polygon_selection.extract_status import (
    extract_status,
    is_country_clean,
)


def _touch_run_json(country_dir: Path) -> None:
    country_dir.mkdir(parents=True, exist_ok=True)
    (country_dir / "01_extracted.jsonl.run.json").write_text("{}")


class TestExtractStatusMerged:
    def test_merged_run_json_returns_clean(self, tmp_path: Path) -> None:
        _touch_run_json(tmp_path / "france")
        assert extract_status(tmp_path / "france") == "clean"

    def test_no_run_json_returns_killed(self, tmp_path: Path) -> None:
        (tmp_path / "albania").mkdir()
        assert extract_status(tmp_path / "albania") == "killed"

    def test_missing_dir_returns_killed(self, tmp_path: Path) -> None:
        assert extract_status(tmp_path / "nonexistent") == "killed"


class TestExtractStatusRegional:
    def test_any_sub_region_run_json_returns_clean(self, tmp_path: Path) -> None:
        country_dir = tmp_path / "italy"
        country_dir.mkdir()
        # No merged run.json, but a sub-region one
        (country_dir / "01_extracted_centro.jsonl.run.json").write_text("{}")
        assert extract_status(country_dir) == "clean"

    def test_multiple_sub_region_run_jsons_returns_clean(
        self, tmp_path: Path
    ) -> None:
        country_dir = tmp_path / "germany"
        country_dir.mkdir()
        (country_dir / "01_extracted_bremen.jsonl.run.json").write_text("{}")
        (country_dir / "01_extracted_bayern.jsonl.run.json").write_text("{}")
        assert extract_status(country_dir) == "clean"

    def test_sub_region_file_without_run_json_returns_killed(
        self, tmp_path: Path
    ) -> None:
        country_dir = tmp_path / "spain"
        country_dir.mkdir()
        # jsonl exists but no run.json
        (country_dir / "01_extracted_madrid.jsonl").write_text("x")
        assert extract_status(country_dir) == "killed"


class TestIsCountryClean:
    def test_returns_true_when_clean(self, tmp_path: Path) -> None:
        _touch_run_json(tmp_path / "france")
        assert is_country_clean(tmp_path / "france") is True

    def test_returns_false_when_killed(self, tmp_path: Path) -> None:
        (tmp_path / "italy").mkdir()
        assert is_country_clean(tmp_path / "italy") is False

    def test_returns_false_when_missing(self, tmp_path: Path) -> None:
        assert is_country_clean(tmp_path / "missing") is False

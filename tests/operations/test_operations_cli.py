"""Tests for the operations CLI builders.

No real curl/uv/Playwright invocation. The tests assert
argparse parsing + the no-op short-circuits in run_europe and
process_regions.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from osm_polygon_selection.operations.cli import (
    build_process_regions_parser,
    build_run_europe_parser,
    process_regions,
    run_europe,
)


class TestBuildRunEuropeParser:
    def test_default_max_seconds(self) -> None:
        args = build_run_europe_parser().parse_args([])
        assert args.max_seconds > 0

    def test_max_seconds_override(self) -> None:
        args = build_run_europe_parser().parse_args(["--max-seconds", "60"])
        assert args.max_seconds == 60

    def test_country_repeatable(self) -> None:
        args = build_run_europe_parser().parse_args(
            ["--country", "france", "--country", "germany"]
        )
        assert args.country == ["france", "germany"]

    def test_no_country_means_all(self) -> None:
        args = build_run_europe_parser().parse_args([])
        assert args.country is None


class TestBuildProcessRegionsParser:
    def test_country_required(self) -> None:
        with pytest.raises(SystemExit):
            build_process_regions_parser().parse_args([])

    def test_country_must_be_known(self) -> None:
        with pytest.raises(SystemExit):
            build_process_regions_parser().parse_args(["unknown"])

    def test_country_france(self) -> None:
        args = build_process_regions_parser().parse_args(["france"])
        assert args.country == "france"
        assert args.regions is None
        assert args.skip_download is False

    def test_regions_subset(self) -> None:
        args = build_process_regions_parser().parse_args(
            ["france", "--regions", "alsace", "bretagne"]
        )
        assert args.regions == ["alsace", "bretagne"]

    def test_skip_download_flag(self) -> None:
        args = build_process_regions_parser().parse_args(
            ["germany", "--skip-download"]
        )
        assert args.skip_download is True

    def test_max_seconds_override(self) -> None:
        args = build_process_regions_parser().parse_args(
            ["germany", "--max-seconds", "300"]
        )
        assert args.max_seconds == 300


class TestProcessRegionsNoDownloads:
    """When all regions are already on disk + skip-download, the
    function should complete without raising or doing real I/O."""

    def test_skip_download_no_pbf_skips_all(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("OSM_DATA_ROOT", str(tmp_path))
        monkeypatch.setenv("OSM_REPO_ROOT", str(tmp_path))
        (tmp_path / "raw").mkdir()
        (tmp_path / "processed").mkdir()
        # No PBFs on disk; all regions are skipped.
        result = process_regions(["germany", "--skip-download", "--regions", "bayern"])
        assert result == 0


class TestRunEuropeNoOp:
    def test_no_pending_countries_returns_zero(
        self, tmp_path: Path, monkeypatch,
    ) -> None:
        """When all countries are already classified, return 0."""
        from osm_polygon_selection.config import RuntimeConfig
        monkeypatch.setenv("OSM_DATA_ROOT", str(tmp_path))
        monkeypatch.setenv("OSM_REPO_ROOT", str(tmp_path))
        proc = tmp_path / "processed"
        proc.mkdir(parents=True, exist_ok=True)
        # All 46 European countries already classified:
        from osm_polygon_selection.operations.europe_loop import (
            EUROPEAN_COUNTRIES,
        )
        for c in EUROPEAN_COUNTRIES:
            country_dir = proc / c
            country_dir.mkdir(parents=True, exist_ok=True)
            (country_dir / "03_classified.jsonl").write_text("a\n")
        result = run_europe(["--max-seconds", "1"])
        assert result == 0


class TestScreenshotModule:
    def test_resolve_output_path_env_override(
        self, monkeypatch, tmp_path: Path,
    ) -> None:
        from osm_polygon_selection.operations.screenshot import resolve_output_path
        target = tmp_path / "x.png"
        monkeypatch.setenv("OSM_MAP_PREVIEW_PNG", str(target))
        assert resolve_output_path() == target

    def test_resolve_output_path_default(
        self, monkeypatch, tmp_path: Path,
    ) -> None:
        from osm_polygon_selection.operations.screenshot import resolve_output_path
        monkeypatch.delenv("OSM_MAP_PREVIEW_PNG", raising=False)
        monkeypatch.setenv("OSM_REPO_ROOT", str(tmp_path))
        assert resolve_output_path() == tmp_path / "data" / "dataset" / "map_preview.png"

    def test_module_constants(self) -> None:
        from osm_polygon_selection.operations.screenshot import (
            HEIGHT, LOAD_WAIT_S, SAMPLE_HTML, WIDTH,
        )
        assert WIDTH == 1600
        assert HEIGHT == 1100
        assert LOAD_WAIT_S == 8
        assert SAMPLE_HTML == Path("/tmp/sample_map.html")

    def test_main_returns_1_when_missing(
        self, tmp_path: Path, monkeypatch,
    ) -> None:
        """main() must exit with 1 when the sample HTML is missing."""
        from osm_polygon_selection.operations import screenshot as sc
        # Patch SAMPLE_HTML to point at a non-existent file.
        monkeypatch.setattr(sc, "SAMPLE_HTML", tmp_path / "missing.html")
        # Now main() must hit the FileNotFoundError branch.
        result = sc.main()
        assert result == 1

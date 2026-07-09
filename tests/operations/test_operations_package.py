"""Tests for the operations package.

No real curl, no real uv subprocesses, no real network. The
package builds commands and orchestration logic; the tests
verify the structure of the commands and the orchestration
decisions using fakes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from osm_polygon_selection.operations.downloads import (
    build_curl_command,
    geofabrik_country_url,
    geofabrik_region_url,
    pbf_is_present,
    region_pbf_name,
)
from osm_polygon_selection.operations.regions import (
    COUNTRY_REGIONS,
    DEFAULT_MAX_SECONDS,
    list_regions,
    region_output_path,
)
from osm_polygon_selection.operations.subprocesses import (
    build_stage0_command,
    build_stage2_command,
    build_stage3_command,
    env_with_data_root,
)


class TestBuildCurlCommand:
    def test_basic_url(self, tmp_path: Path) -> None:
        cmd = build_curl_command("https://example.com/x.pbf", tmp_path / "x.pbf")
        assert cmd[0] == "curl"
        assert "-L" in cmd
        assert "-s" in cmd
        assert "-o" in cmd
        assert str(tmp_path / "x.pbf") in cmd
        assert "https://example.com/x.pbf" in cmd

    def test_timeout_default_600(self, tmp_path: Path) -> None:
        cmd = build_curl_command("u", tmp_path / "x")
        assert "--max-time" in cmd
        idx = cmd.index("--max-time")
        assert cmd[idx + 1] == "600"

    def test_timeout_override(self, tmp_path: Path) -> None:
        cmd = build_curl_command("u", tmp_path / "x", timeout_s=42)
        idx = cmd.index("--max-time")
        assert cmd[idx + 1] == "42"


class TestGeofabrikUrls:
    def test_country_url(self) -> None:
        url = geofabrik_country_url("france")
        assert url == "https://download.geofabrik.de/europe/france-latest.osm.pbf"

    def test_region_url(self) -> None:
        url = geofabrik_region_url("france", "alsace")
        assert url == "https://download.geofabrik.de/europe/france/alsace-latest.osm.pbf"


class TestPbfIsPresent:
    def test_missing(self, tmp_path: Path) -> None:
        assert not pbf_is_present(tmp_path / "nope.pbf")

    def test_empty_file(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.pbf"
        p.write_text("")
        assert not pbf_is_present(p)

    def test_small_file_below_threshold(self, tmp_path: Path) -> None:
        p = tmp_path / "small.pbf"
        p.write_bytes(b"x" * 100)
        assert not pbf_is_present(p)

    def test_large_file(self, tmp_path: Path) -> None:
        p = tmp_path / "big.pbf"
        p.write_bytes(b"x" * 2000)
        assert pbf_is_present(p)

    def test_min_size_override(self, tmp_path: Path) -> None:
        p = tmp_path / "p"
        p.write_bytes(b"x" * 500)
        assert not pbf_is_present(p, min_size_bytes=10_000)
        assert pbf_is_present(p, min_size_bytes=100)


class TestRegionPbfName:
    def test_format(self) -> None:
        assert region_pbf_name("alsace") == "alsace-latest.osm.pbf"


class TestBuildStageCommands:
    def test_stage0_basic(self, tmp_path: Path) -> None:
        cmd = build_stage0_command(tmp_path / "in.pbf", tmp_path / "out.jsonl")
        assert cmd[0:2] == ["uv", "run"]
        assert "scripts/pipeline/stage0_extract.py" in cmd
        assert str(tmp_path / "in.pbf") in cmd
        assert str(tmp_path / "out.jsonl") in cmd

    def test_stage0_with_max_seconds(self, tmp_path: Path) -> None:
        cmd = build_stage0_command(
            tmp_path / "in.pbf", tmp_path / "out.jsonl", max_seconds=120,
        )
        assert "--max-seconds" in cmd
        assert "120" in cmd

    def test_stage0_without_max_seconds_omits_flag(self, tmp_path: Path) -> None:
        cmd = build_stage0_command(tmp_path / "in.pbf", tmp_path / "out.jsonl")
        assert "--max-seconds" not in cmd

    def test_stage2(self, tmp_path: Path) -> None:
        cmd = build_stage2_command(
            tmp_path / "in.jsonl", tmp_path / "wl.json", tmp_path / "out.jsonl",
        )
        assert "scripts/pipeline/stage2_filter.py" in cmd
        assert str(tmp_path / "in.jsonl") in cmd
        assert str(tmp_path / "wl.json") in cmd
        assert str(tmp_path / "out.jsonl") in cmd

    def test_stage3(self, tmp_path: Path) -> None:
        cmd = build_stage3_command(
            tmp_path / "in.jsonl", tmp_path / "ne.shp", tmp_path / "out.jsonl",
        )
        assert "scripts/pipeline/stage3_classify.py" in cmd
        assert str(tmp_path / "ne.shp") in cmd


class TestEnvWithDataRoot:
    def test_returns_dict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OSM_DATA_ROOT", "/foo/bar")
        env = env_with_data_root()
        assert env["OSM_DATA_ROOT"] == "/foo/bar"

    def test_extra_env_overrides(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OSM_DATA_ROOT", "/old")
        env = env_with_data_root({"OSM_DATA_ROOT": "/new"})
        assert env["OSM_DATA_ROOT"] == "/new"


class TestRegionOutputPath:
    def test_creates_country_dir(self, tmp_path: Path) -> None:
        out = region_output_path(tmp_path, "france", "alsace")
        assert out == tmp_path / "france" / "01_extracted_alsace.jsonl"
        assert (tmp_path / "france").is_dir()

    def test_does_not_create_output_file(self, tmp_path: Path) -> None:
        out = region_output_path(tmp_path, "germany", "bayern")
        assert not out.exists()


class TestListRegions:
    def test_full_list(self) -> None:
        assert list_regions("france") == COUNTRY_REGIONS["france"]
        assert list_regions("germany") == COUNTRY_REGIONS["germany"]

    def test_only_subset(self) -> None:
        only = ["alsace", "bretagne", "ile-de-france"]
        out = list_regions("france", only)
        assert out == ["alsace", "bretagne", "ile-de-france"]

    def test_only_filters_unknown(self) -> None:
        only = ["alsace", "nope", "bretagne"]
        out = list_regions("france", only)
        assert out == ["alsace", "bretagne"]


class TestEuropeLoopHelpers:
    def test_default_max_seconds_positive(self) -> None:
        from osm_polygon_selection.operations.europe_loop import DEFAULT_EXTRACT_WAIT_S
        assert DEFAULT_EXTRACT_WAIT_S > 0

    def test_european_countries_non_empty(self) -> None:
        from osm_polygon_selection.operations.europe_loop import EUROPEAN_COUNTRIES
        assert len(EUROPEAN_COUNTRIES) >= 40
        assert "france" in EUROPEAN_COUNTRIES
        assert "germany" in EUROPEAN_COUNTRIES

    def test_count_lines_missing(self, tmp_path: Path) -> None:
        from osm_polygon_selection.operations.europe_loop import count_lines
        assert count_lines(tmp_path / "missing.jsonl") == 0

    def test_count_lines_present(self, tmp_path: Path) -> None:
        from osm_polygon_selection.operations.europe_loop import count_lines
        p = tmp_path / "lines.jsonl"
        p.write_text("a\nb\nc\n")
        assert count_lines(p) == 3

    def test_is_classified(self, tmp_path: Path) -> None:
        from osm_polygon_selection.operations.europe_loop import is_classified
        d = tmp_path / "x"
        d.mkdir()
        assert not is_classified(d)
        (d / "03_classified.jsonl").write_text("a\n")
        assert is_classified(d)

    def test_has_extracted(self, tmp_path: Path) -> None:
        from osm_polygon_selection.operations.europe_loop import has_extracted
        d = tmp_path / "y"
        d.mkdir()
        assert not has_extracted(d)
        (d / "01_extracted.jsonl").write_text("x" * 200)
        assert has_extracted(d)

    def test_read_progress_missing(self, tmp_path: Path) -> None:
        from osm_polygon_selection.operations.europe_loop import read_progress
        assert read_progress(tmp_path) == {}

    def test_read_progress_malformed(self, tmp_path: Path) -> None:
        from osm_polygon_selection.operations.europe_loop import read_progress
        (tmp_path / "01_extracted.jsonl.progress.json").write_text("not json")
        assert read_progress(tmp_path) == {}

    def test_read_progress_valid(self, tmp_path: Path) -> None:
        from osm_polygon_selection.operations.europe_loop import read_progress
        (tmp_path / "01_extracted.jsonl.progress.json").write_text('{"n": 5}')
        assert read_progress(tmp_path) == {"n": 5}

    def test_complete_stages_stage2_failure_returns_zero(
        self, tmp_path: Path,
    ) -> None:
        from osm_polygon_selection.operations.europe_loop import complete_stages
        shp = tmp_path / "ne.shp"
        shp.write_text("")
        n = complete_stages(
            country="x",
            proc_dir=tmp_path,
            hdd_root=tmp_path,
            proj=tmp_path,
            shp=shp,
        )
        # Stage 2 fails because the input jsonl doesn't exist
        # (or the subprocess fails); the wrapper returns 0.
        assert n == 0

    def test_natural_earth_shp_constant(self) -> None:
        from osm_polygon_selection.operations.europe_loop import NATURAL_EARTH_SHP
        assert "ne_110m_admin_0_countries.shp" in NATURAL_EARTH_SHP

    def test_pbf_present_helper_preexisting(self, tmp_path: Path) -> None:
        from osm_polygon_selection.operations.europe_loop import (
            download_country_pbf,
        )
        raw = tmp_path / "raw"
        raw.mkdir()
        existing = raw / "france-latest.osm.pbf"
        existing.write_bytes(b"x" * 2000)
        result = download_country_pbf(raw, "france")
        assert result is True


class TestRegionsHelpers:
    def test_resolve_proj_default(self, monkeypatch) -> None:
        from osm_polygon_selection.operations.regions import resolve_proj
        monkeypatch.delenv("OSM_REPO_ROOT", raising=False)
        # The default falls back to project_root().
        p = resolve_proj()
        assert p.exists() or p == Path.cwd().resolve()

    def test_resolve_proj_with_env(self, tmp_path: Path, monkeypatch) -> None:
        from osm_polygon_selection.operations.regions import resolve_proj
        monkeypatch.setenv("OSM_REPO_ROOT", str(tmp_path))
        assert resolve_proj() == tmp_path

    def test_region_output_path(self, tmp_path: Path) -> None:
        from osm_polygon_selection.operations.regions import region_output_path
        out = region_output_path(tmp_path, "france", "alsace")
        assert out == tmp_path / "france" / "01_extracted_alsace.jsonl"

    def test_download_region_preexisting(self, tmp_path: Path) -> None:
        from osm_polygon_selection.operations.regions import download_region
        existing = tmp_path / "alsace-latest.osm.pbf"
        existing.write_bytes(b"x" * 2_000_000)
        pbf = download_region(
            region="alsace", country="france", raw_dir=tmp_path,
        )
        assert pbf == existing

    def test_extract_region_no_output(self, tmp_path: Path) -> None:
        from osm_polygon_selection.operations.regions import extract_region
        pbf = tmp_path / "x.pbf"
        pbf.write_bytes(b"x" * 100)
        n = extract_region(
            region="alsace", pbf=pbf, country="france",
            proc_dir=tmp_path, max_seconds=1,
        )
        # subprocess fails (uv not invoked properly in this test);
        # the function returns 0 because the output file doesn't exist.
        assert n == 0

    def test_list_regions_unknown_only(self) -> None:
        from osm_polygon_selection.operations.regions import list_regions
        # All unknown: filter to empty list.
        assert list_regions("france", ["nonexistent"]) == []

    def test_default_max_seconds(self) -> None:
        from osm_polygon_selection.operations.regions import DEFAULT_MAX_SECONDS
        assert DEFAULT_MAX_SECONDS > 0

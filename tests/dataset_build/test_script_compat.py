"""Tests for the script_compat module (legacy compat shims).

These test the public behavior of the script-compat module:
ScriptConfig, build_country_table, build_schema, pbf_date_for,
row_to_record, process_country, write_readme, extract_status.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from osm_polygon_selection.dataset_build.script_compat import (
    ScriptConfig,
    build_country_table,
    build_schema,
    extract_status,
    make_config,
    pbf_date_for,
    process_country,
    row_to_record,
    write_readme,
)


class TestScriptConfig:
    def test_defaults(self) -> None:
        cfg = make_config(Path("/tmp/hdd"), Path("/tmp/proc"), "wkt")
        assert cfg.HDD == Path("/tmp/hdd")
        assert cfg.PROC == Path("/tmp/proc")
        assert cfg.geometry_encoding == "wkt"

    def test_explicit_geometry(self) -> None:
        cfg = make_config(Path("/h"), Path("/p"), "wkb")
        assert cfg.geometry_encoding == "wkb"

    def test_direct_construction(self) -> None:
        cfg = ScriptConfig(HDD=Path("/h"), PROC=Path("/p"), geometry_encoding="none")
        assert cfg.geometry_encoding == "none"


class TestBuildSchema:
    def test_default_wkt(self) -> None:
        cfg = make_config(Path("/h"), Path("/p"), "wkt")
        schema = build_schema(cfg)
        names = [f.name for f in schema]
        assert "geometry_wkt" in names
        assert "geometry_wkb" not in names

    def test_wkb(self) -> None:
        cfg = make_config(Path("/h"), Path("/p"), "wkb")
        schema = build_schema(cfg)
        names = [f.name for f in schema]
        assert "geometry_wkb" in names
        assert "geometry_wkt" not in names

    def test_none(self) -> None:
        cfg = make_config(Path("/h"), Path("/p"), "none")
        schema = build_schema(cfg)
        names = [f.name for f in schema]
        assert "geometry_wkt" not in names
        assert "geometry_wkb" not in names


class TestBuildCountryTable:
    def test_empty_list(self) -> None:
        cfg = make_config(Path("/h"), Path("/p"), "wkt")
        out = build_country_table(cfg, [])
        assert "0" in out
        assert "Total" in out

    def test_sorts_alphabetically(self) -> None:
        cfg = make_config(Path("/h"), Path("/p"), "wkt")
        out = build_country_table(
            cfg,
            [
                {"country": "zimbabwe", "n_polygons": 1, "extract_status": "clean"},
                {"country": "albania", "n_polygons": 2, "extract_status": "clean"},
            ],
        )
        lines = out.split("\n")
        assert "albania" in lines[2]
        assert "zimbabwe" in lines[3]

    def test_total_row_present(self) -> None:
        cfg = make_config(Path("/h"), Path("/p"), "wkt")
        out = build_country_table(
            cfg,
            [
                {"country": "albania", "n_polygons": 100, "extract_status": "clean"},
                {"country": "france", "n_polygons": 200, "extract_status": "clean"},
            ],
        )
        assert "300" in out
        assert "**Total**" in out


class TestPbfDateFor:
    def test_missing_pbf_returns_unknown(self, tmp_path: Path) -> None:
        cfg = make_config(tmp_path, tmp_path / "proc", "wkt")
        assert pbf_date_for(cfg, "nowhere") == "unknown"

    def test_existing_pbf_returns_iso_date(self, tmp_path: Path) -> None:
        import os
        raw = tmp_path / "raw"
        raw.mkdir()
        target = 1722470400
        pbf = raw / "liechtenstein-latest.osm.pbf"
        pbf.write_text("x")
        os.utime(pbf, (target, target))
        cfg = make_config(tmp_path, tmp_path / "proc", "wkt")
        assert pbf_date_for(cfg, "liechtenstein") == "2024-08-01"


class TestExtractStatus:
    def test_no_run_json_returns_killed(self, tmp_path: Path) -> None:
        proc = tmp_path / "proc"
        proc.mkdir()
        cfg = make_config(tmp_path, proc, "wkt")
        (proc / "italy").mkdir()
        assert extract_status(cfg, "italy") == "killed"

    def test_missing_country_dir_returns_killed(self, tmp_path: Path) -> None:
        proc = tmp_path / "proc"
        proc.mkdir()
        cfg = make_config(tmp_path, proc, "wkt")
        assert extract_status(cfg, "nowhere") == "killed"

    def test_merged_run_json_returns_clean(self, tmp_path: Path) -> None:
        proc = tmp_path / "proc"
        proc.mkdir()
        country_dir = proc / "france"
        country_dir.mkdir()
        (country_dir / "01_extracted.jsonl.run.json").write_text("{}")
        cfg = make_config(tmp_path, proc, "wkt")
        assert extract_status(cfg, "france") == "clean"


class TestWriteReadme:
    def test_writes_file(self, tmp_path: Path, monkeypatch) -> None:
        """End-to-end smoke: build the dataset layout, call write_readme."""
        from osm_polygon_selection.dataset_build.config import PIPELINE_VERSION
        # Build the minimum dataset layout the readme renderer expects.
        from osm_polygon_selection.dataset_layout import ensure_layout
        ensure_layout(tmp_path)
        cfg = make_config(Path("/h"), Path("/p"), "wkt")
        out_dir = tmp_path  # ensure_layout created subdirs under tmp_path
        write_readme(
            cfg, out_dir,
            countries_done=[{"country": "albania", "n_polygons": 100, "extract_status": "clean"}],
            total_polygons=100,
            pipeline_version=PIPELINE_VERSION,
        )
        readme = out_dir / "README.md"
        assert readme.exists()
        text = readme.read_text()
        assert "albania" in text

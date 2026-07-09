"""Tests for the build_dataset script.

Domain behavior is now tested through package modules; only
the script-level entry point (env-var validation, main()
delegation) is tested against the script source.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pyarrow as pa
import pytest

BUILD_DATASET_PATH = Path(__file__).resolve().parents[2] / "scripts" / "build_dataset.py"


# ---------------------------------------------------------------------------
# Package-level: schema / row_to_record / dataset_dir behavior
# ---------------------------------------------------------------------------


class TestDatasetSchema:
    """The published dataset MUST have a geometry column.

    Tested at the package boundary (``schema_defs.build_schema``)
    so the test does not need to re-execute the script source.
    """

    def test_default_schema_has_geometry_wkt(self) -> None:
        from osm_polygon_selection.schema_defs import build_schema
        names = [f.name for f in build_schema(geometry_encoding="wkt")]
        assert "geometry_wkt" in names, f"Default schema missing geometry_wkt; got {names}"

    def test_wkt_encoding_has_geometry_wkt(self) -> None:
        from osm_polygon_selection.schema_defs import build_schema
        names = [(f.name, f.type) for f in build_schema(geometry_encoding="wkt")]
        assert any(n == "geometry_wkt" for n, _ in names)

    def test_wkb_encoding_has_geometry_wkb(self) -> None:
        from osm_polygon_selection.schema_defs import build_schema
        names = [(f.name, f.type) for f in build_schema(geometry_encoding="wkb")]
        assert any(n == "geometry_wkb" for n, _ in names), (
            f"wkb schema missing geometry_wkb; got {names}"
        )
        for n, t in names:
            if n == "geometry_wkb":
                assert t == pa.binary(), f"geometry_wkb should be binary; got {t}"

    def test_none_encoding_drops_geometry(self) -> None:
        from osm_polygon_selection.schema_defs import build_schema
        names = [f.name for f in build_schema(geometry_encoding="none")]
        assert "geometry_wkt" not in names
        assert "geometry_wkb" not in names


class TestRowToRecord:
    """The row converter must pipe the WKT through into the geometry column."""

    def test_row_has_geometry_wkt_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OSM_POLYGON_GEOMETRY", raising=False)
        from osm_polygon_selection.dataset_build.records import row_to_record
        row = {
            "osm_id": 1,
            "osm_type": "way",
            "centroid": [0.0, 0.0],
            "area_km2": 1.0,
            "tags": ["landuse=forest"],
            "continent": "Europe",
            "size_bin": "small",
            "geometry": "POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))",
        }
        rec = row_to_record(
            row,
            country="test",
            status="clean",
            pbf_date="2026-06-29",
            geometry_encoding="wkt",
            whitelist={"landuse=forest"},
        )
        assert rec is not None
        assert "geometry_wkt" in rec
        assert rec["geometry_wkt"].startswith("POLYGON")


class TestDatasetDir:
    """The dataset output directory is configurable via OSM_DATASET_DIR."""

    def test_default_dataset_dir_under_repo(self) -> None:
        from osm_polygon_selection.config import dataset_root, project_root
        default = dataset_root()
        # default is a sibling of the project repo (ext-HDD-friendly)
        assert default.name == "osm-polygon-selection-dataset"
        assert default.parent == project_root().parent

    def test_external_hdd_overrides(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OSM_DATASET_DIR", "/Volumes/Seagate M3/test")
        from osm_polygon_selection.config import dataset_root
        assert str(dataset_root()) == "/Volumes/Seagate M3/test"


# ---------------------------------------------------------------------------
# Script-level: only the env-var validation + main() delegation
# ---------------------------------------------------------------------------


class TestScriptEnvValidation:
    """The script must SystemExit on invalid OSM_POLYGON_GEOMETRY values."""

    def test_invalid_encoding_fails(self) -> None:
        env = {**os.environ, "OSM_POLYGON_GEOMETRY": "garbage"}
        result = subprocess.run(
            [sys.executable, str(BUILD_DATASET_PATH)],
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, (
            f"Script should fail on bad env. stdout={result.stdout!r} "
            f"stderr={result.stderr!r}"
        )
        assert "OSM_POLYGON_GEOMETRY" in result.stderr


class TestScriptWrappers:
    """The script re-exports the package wrappers for backwards-compat tests."""

    def test_script_exposes_legacy_helpers(self) -> None:
        """The script must still expose row_to_record / pbf_date_for / etc."""
        spec = importlib.util.spec_from_file_location("build_dataset", BUILD_DATASET_PATH)
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        sys.modules["build_dataset"] = mod
        try:
            spec.loader.exec_module(mod)
            assert callable(mod.row_to_record)
            assert callable(mod.pbf_date_for)
            assert callable(mod.build_country_table)
        finally:
            sys.modules.pop("build_dataset", None)

    def test_main_delegates_to_run_build_dataset(self) -> None:
        """``main()`` should call the CLI runner.

        Verified statically: the script's source must include a
        call to the CLI ``main`` (which calls
        ``run_build_dataset``).
        """
        src = BUILD_DATASET_PATH.read_text()
        # The script delegates to the cli/build_dataset module
        # which calls run_build_dataset. The canonical main
        # definition must be reachable from the root script
        # (either via direct re-export or via the exec trick).
        # We assert the cli module's main is wired to
        # run_build_dataset, and that the canonical script file
        # contains a main() that delegates to the cli.
        canonical = (
            Path(__file__).resolve().parents[2]
            / "scripts" / "dataset" / "build_dataset.py"
        )
        canonical_src = canonical.read_text()
        assert "def main() -> None:" in canonical_src
        assert "_cli_main" in canonical_src
        # And the cli module does the actual call.
        from osm_polygon_selection.cli.build_dataset import main as cli_main
        import inspect
        cli_src = inspect.getsource(cli_main)
        assert "run_build_dataset" in cli_src

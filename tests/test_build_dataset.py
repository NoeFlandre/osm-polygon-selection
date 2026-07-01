"""Tests for the build_dataset script.

These tests ensure the published HF dataset has the geometry
column and other invariants. They do NOT download the actual
4+GB parquet files - they only check the schema and build
processes that generate the data.
"""

import importlib.util
import os
import sys
from pathlib import Path

import pyarrow as pa
import pytest

# Load build_dataset.py as a module (it's in scripts/, not a package)
BUILD_DATASET = Path(__file__).resolve().parents[1] / "scripts" / "build_dataset.py"
spec = importlib.util.spec_from_file_location("build_dataset", BUILD_DATASET)
if spec is None or spec.loader is None:
    raise ImportError(f"could not load {BUILD_DATASET}")
build_dataset = importlib.util.module_from_spec(spec)
sys.modules["build_dataset"] = build_dataset
spec.loader.exec_module(build_dataset)


class TestDatasetSchema:
    """The published dataset MUST have a geometry column.

    We re-execute the module source for each test to pick up
    OSM_POLYGON_GEOMETRY env changes (reloading the same module
    object is tricky because the import-time checks would have
    already rejected invalid values).
    """

    def _fresh_module(self, env: dict[str, str] | None = None):
        """Execute build_dataset.py source with the given env vars."""
        old = {k: os.environ.get(k) for k in (env or {}).keys()}
        try:
            if env is not None:
                for k, v in env.items():
                    if v == "":
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v
            # Re-execute the module's source
            code = compile(BUILD_DATASET.read_text(), str(BUILD_DATASET), "exec")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_default_schema_has_geometry_wkt(self):
        """OSM_POLYGON_GEOMETRY unset => geometry_wkt column."""
        mod = self._fresh_module(env={"OSM_POLYGON_GEOMETRY": ""})
        names = [f.name for f in mod.build_schema()]
        assert "geometry_wkt" in names, f"Default schema missing geometry_wkt; got {names}"

    def test_wkt_encoding_has_geometry_wkt(self):
        """OSM_POLYGON_GEOMETRY=wkt (explicit) => geometry_wkt column."""
        mod = self._fresh_module(env={"OSM_POLYGON_GEOMETRY": "wkt"})
        names = [(f.name, f.type) for f in mod.build_schema()]
        assert any(n == "geometry_wkt" for n, _ in names)

    def test_wkb_encoding_has_geometry_wkb(self):
        """OSM_POLYGON_GEOMETRY=wkb => geometry_wkb column (binary)."""
        mod = self._fresh_module(env={"OSM_POLYGON_GEOMETRY": "wkb"})
        schema = mod.build_schema()
        names = [(f.name, f.type) for f in schema]
        assert any(n == "geometry_wkb" for n, _ in names), (
            f"wkb schema missing geometry_wkb; got {names}"
        )
        for n, t in names:
            if n == "geometry_wkb":
                assert t == pa.binary(), f"geometry_wkb should be binary; got {t}"

    def test_none_encoding_drops_geometry(self):
        """OSM_POLYGON_GEOMETRY=none => no geometry column at all."""
        mod = self._fresh_module(env={"OSM_POLYGON_GEOMETRY": "none"})
        names = [f.name for f in mod.build_schema()]
        assert "geometry_wkt" not in names
        assert "geometry_wkb" not in names

    def test_invalid_encoding_fails(self):
        """OSM_POLYGON_GEOMETRY=garbage => fail loud at import."""
        with pytest.raises(SystemExit):
            self._fresh_module(env={"OSM_POLYGON_GEOMETRY": "garbage"})


class TestRowToRecord:
    """The row converter must pipe the WKT through into the geometry column."""

    def test_row_has_geometry_wkt_by_default(self):
        mod = build_dataset  # uses env from test setup
        # Re-fresh with no env override
        old = os.environ.pop("OSM_POLYGON_GEOMETRY", None)
        try:
            fresh = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(fresh)
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
            rec = fresh.row_to_record(row, "test", "clean", "2026-06-29")
            assert "geometry_wkt" in rec
            assert rec["geometry_wkt"].startswith("POLYGON")
        finally:
            if old is not None:
                os.environ["OSM_POLYGON_GEOMETRY"] = old


class TestDatasetDir:
    """The dataset output directory is configurable via OSM_DATASET_DIR."""

    def test_default_dataset_dir_under_repo(self):
        # Default should be a sibling of the project repo (ext-HDD-friendly)
        assert build_dataset.DATASET_DIR.name == "osm-polygon-selection-dataset"
        # parents[1] of scripts/build_dataset.py = project root; its parent is the dataset root's parent
        assert build_dataset.DATASET_DIR.parent == Path(build_dataset.__file__).resolve().parents[1].parent

    def test_external_hdd_overrides(self):
        old = os.environ.get("OSM_DATASET_DIR")
        try:
            os.environ["OSM_DATASET_DIR"] = "/Volumes/Seagate M3/test"
            fresh = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(fresh)
            assert str(fresh.DATASET_DIR) == "/Volumes/Seagate M3/test"
        finally:
            if old is None:
                os.environ.pop("OSM_DATASET_DIR", None)
            else:
                os.environ["OSM_DATASET_DIR"] = old

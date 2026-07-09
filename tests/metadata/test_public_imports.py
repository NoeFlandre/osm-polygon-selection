"""Pin the public import surface of the package.

Each entry asserts that a public module path still exposes the
named symbols. These are compatibility pins: when a module
moves into a subpackage, the old path becomes a thin facade
and must keep re-exporting the same names so existing imports
keep working.
"""

from __future__ import annotations

import pytest


PUBLIC_IMPORTS = [
    # (path, expected name)
    ("osm_polygon_selection.runtime_config", "RuntimeConfig"),
    ("osm_polygon_selection.paths", "dataset_root"),
    ("osm_polygon_selection.git_meta", "git_short_sha"),
    ("osm_polygon_selection.git_meta", "repo_root"),
    ("osm_polygon_selection.schema_defs", "build_schema"),
    ("osm_polygon_selection.pyarrow_compat", "value_counts"),
    ("osm_polygon_selection.whitelist_io", "load_whitelist"),
    ("osm_polygon_selection.whitelist_io", "compute_matched_tag"),
    ("osm_polygon_selection.country_table", "build_country_table"),
    ("osm_polygon_selection.readme_render", "build_root_readme"),
    ("osm_polygon_selection.readme_render", "build_folder_readme"),
    ("osm_polygon_selection.readme_render", "build_country_readme"),
    ("osm_polygon_selection.readme_render", "write_metadata_yaml"),
    ("osm_polygon_selection.sample_table", "compute_global_size_bin_distribution"),
    ("osm_polygon_selection.sample_table", "compute_sample_size_bin_distribution"),
    ("osm_polygon_selection.sample_table", "build_example_row_table"),
    ("osm_polygon_selection.sample_table", "build_size_bin_distribution_table"),
    ("osm_polygon_selection.streaming_writer", "write_jsonl_to_parquet"),
    ("osm_polygon_selection.streaming_writer", "CHUNK_SIZE"),
    ("osm_polygon_selection.stages.extract", "extract"),
    ("osm_polygon_selection.stages.extract", "MIN_AREA_KM2"),
    ("osm_polygon_selection.stages.extract", "MAX_AREA_KM2"),
    ("osm_polygon_selection.stages.extract", "record_from_wkt"),
    ("osm_polygon_selection.pbf_meta", "NON_EUROPE_COUNTRIES"),
    ("osm_polygon_selection.pbf_meta", "geofabrik_url"),
    ("osm_polygon_selection.pbf_meta", "pbf_date_for"),
    ("osm_polygon_selection.country_notes", "COUNTRY_NOTES"),
    ("osm_polygon_selection.country_notes", "REGIONAL_SUB_PBFS"),
    ("osm_polygon_selection.country_notes", "country_note"),
    ("osm_polygon_selection.country_notes", "country_source_description"),
    # The backwards-compat facade at the old single-file path.
    ("osm_polygon_selection.regional_pbf_meta", "REGIONAL_SUB_PBFS_CANONICAL"),
    ("osm_polygon_selection.regional_pbf_meta", "ALL_REGIONAL_CANONICAL"),
    # Extract-status facade.
    ("osm_polygon_selection.extract_status", "extract_status"),
    ("osm_polygon_selection.extract_status", "is_country_clean"),
    # Streaming-writer private alias (kept for tests).
    ("osm_polygon_selection.streaming_writer", "_write_jsonl_to_parquet_python_json"),
    # Git-meta facade.
    ("osm_polygon_selection.git_meta", "git_sha"),
]


# Names that look like they might be re-exported (legacy compat) but
# are intentionally NOT part of the public surface. If anyone adds
# them to records/__init__ by accident, this test will fail.
PUBLIC_NON_IMPORTS = [
    ("osm_polygon_selection.stages.extract_stage.records", "make_valid"),
    ("osm_polygon_selection.stages.extract_stage.records", "is_polygon"),
]


@pytest.mark.parametrize(
    "path,name",
    PUBLIC_NON_IMPORTS,
    ids=lambda v: f"{v[0]}.{v[1]}" if isinstance(v, tuple) else v,
)
def test_public_records_does_not_re_export_legacy_helpers(
    path: str, name: str,
) -> None:
    """Records module no longer re-exports shapely helpers as compat."""
    # Use the same import path that production callers do (via
    # ``stages.extract``), so we don't trigger the package's own
    # partially-initialized-module fragility.
    import importlib
    mod = importlib.import_module("osm_polygon_selection.stages.extract")
    records_mod = importlib.import_module(
        "osm_polygon_selection.stages.extract_stage.records"
    )
    del mod  # silence unused; the side effect is what matters
    assert not hasattr(records_mod, name), (
        f"records unexpectedly exposes {name!r}; the legacy compat shim "
        f"was removed, so this attribute should not return."
    )


@pytest.mark.parametrize("path,name", PUBLIC_IMPORTS, ids=lambda v: v if isinstance(v, str) else f"{v[0]}.{v[1]}")
def test_public_import_exposes_name(path: str, name: str) -> None:
    """Old import paths still expose the documented names."""
    import importlib
    # Force the parent package to be imported first so the
    # sys.modules aliases are installed.
    parent = path.rsplit(".", 1)[0]
    importlib.import_module(parent)
    mod = importlib.import_module(path)
    assert hasattr(mod, name), (
        f"{path} no longer exposes {name!r} (compatibility regression)"
    )

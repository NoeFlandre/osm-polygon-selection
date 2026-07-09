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
]


@pytest.mark.parametrize("path,name", PUBLIC_IMPORTS, ids=lambda v: v if isinstance(v, str) else f"{v[0]}.{v[1]}")
def test_public_import_exposes_name(path: str, name: str) -> None:
    """Old import paths still expose the documented names."""
    import importlib
    mod = importlib.import_module(path)
    assert hasattr(mod, name), (
        f"{path} no longer exposes {name!r} (compatibility regression)"
    )

"""Thin entry point for the dataset build pipeline.

Env-var parsing + module-level config knobs (``HDD``/``PROC``/
``GEOMETRY_ENCODING``) for downstream tests; delegates the
build to :mod:`osm_polygon_selection.cli.build_dataset`. Legacy
wrappers come from :mod:`osm_polygon_selection.dataset_build.script_compat`.
``OSM_POLYGON_GEOMETRY``: ``wkt`` (default), ``wkb``, or ``none``.
"""

from __future__ import annotations

import os
from pathlib import Path

from osm_polygon_selection.cli.build_dataset import main as _cli_main
from osm_polygon_selection.config import RuntimeConfig
from osm_polygon_selection.config.paths import dataset_root
from osm_polygon_selection.dataset_build.config import (  # noqa: F401
    PIPELINE_VERSION, WHITELIST_PATH,
)
from osm_polygon_selection.dataset_build.script_compat import (  # noqa: F401
    ScriptConfig, _encode_geometry, _load_whitelist, _load_whitelist_module_path,
    build_country_table as _sc_build_country_table,
    build_schema as _sc_build_schema,
    extract_status as _sc_extract_status,
    pbf_date_for as _sc_pbf_date_for,
    process_country as _sc_process_country,
    row_to_record as _sc_row_to_record,
    write_readme as _sc_write_readme,
)

_GEOMETRY_ENCODING = os.environ.get("OSM_POLYGON_GEOMETRY", "wkt").lower()
if _GEOMETRY_ENCODING not in ("wkt", "wkb", "none"):
    raise SystemExit(f"OSM_POLYGON_GEOMETRY must be wkt, wkb, or none; got {_GEOMETRY_ENCODING!r}")
GEOMETRY_ENCODING: str = _GEOMETRY_ENCODING

_RUNTIME_CONFIG = RuntimeConfig.from_env()
HDD: Path = _RUNTIME_CONFIG.data_root
PROC: Path = _RUNTIME_CONFIG.processed_root
DATASET_DIR: Path = dataset_root()


def _cfg() -> ScriptConfig:
    return ScriptConfig(HDD=HDD, PROC=PROC, geometry_encoding=GEOMETRY_ENCODING)


def _caller(fn, *extra):
    """Bind a script-compat function to the current module globals."""
    def wrapper(*args, **kwargs):
        return fn(_cfg(), *args, *extra, **kwargs)
    return wrapper  # noqa: E704


extract_status = _caller(_sc_extract_status)
build_schema = _caller(_sc_build_schema)
row_to_record = _caller(_sc_row_to_record)
pbf_date_for = _caller(_sc_pbf_date_for)
process_country = _caller(_sc_process_country, WHITELIST_PATH)
build_country_table = _caller(_sc_build_country_table)


def write_readme(out_dir: Path, countries_done: list[dict], total_polygons: int) -> None:
    _sc_write_readme(_cfg(), out_dir, countries_done, total_polygons, PIPELINE_VERSION)


def main() -> None:
    _cli_main()


__all__ = [
    "DATASET_DIR", "GEOMETRY_ENCODING", "HDD", "PIPELINE_VERSION", "PROC",
    "WHITELIST_PATH", "_encode_geometry", "_load_whitelist",
    "_load_whitelist_module_path", "build_country_table", "build_schema",
    "extract_status", "main", "pbf_date_for", "process_country",
    "row_to_record", "write_readme",
]
if __name__ == "__main__":
    main()

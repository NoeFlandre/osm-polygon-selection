"""Thin entry point for the dataset build pipeline.

Parses environment variables, exposes module-level config knobs
(for downstream tests), and delegates the actual build to
``osm_polygon_selection.dataset_build.runner.run_build_dataset``.

Format controlled by OSM_POLYGON_GEOMETRY:

  OSM_POLYGON_GEOMETRY=wkt    (default) — keep geometry as WKT (text)
  OSM_POLYGON_GEOMETRY=wkb    — keep geometry as WKB (binary, ~50% smaller)
  OSM_POLYGON_GEOMETRY=none   — drop geometry (centroid + area only)
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import pyarrow as pa

# Env-var parsing done at import time so re-execution under a
# different env (as some characterization tests do) re-reads the
# environment. Imports below come after the env-var check so the
# validation runs even on first import.
_GEOMETRY_ENCODING = os.environ.get("OSM_POLYGON_GEOMETRY", "wkt").lower()
if _GEOMETRY_ENCODING not in ("wkt", "wkb", "none"):
    raise SystemExit(
        f"OSM_POLYGON_GEOMETRY must be wkt, wkb, or none; got {_GEOMETRY_ENCODING!r}"
    )
GEOMETRY_ENCODING: str = _GEOMETRY_ENCODING

from osm_polygon_selection.runtime_config import RuntimeConfig  # noqa: E402

_RUNTIME_CONFIG = RuntimeConfig.from_env()
HDD: Path = _RUNTIME_CONFIG.data_root
PROC: Path = _RUNTIME_CONFIG.processed_root

from osm_polygon_selection.paths import dataset_root  # noqa: E402

DATASET_DIR: Path = dataset_root()  # honors $OSM_DATASET_DIR

from osm_polygon_selection.dataset_build.config import (  # noqa: E402,F401
    PIPELINE_VERSION,
    WHITELIST_PATH,
)

# Re-export the streaming writer import so characterization tests
# that grep the script source for it still find it. The actual call
# is in dataset_build.runner._process_classified_country, with a
# per-row Python fallback that calls row_to_record if the streaming
# writer fails (see runner.py: "falling back to per-row path").
from osm_polygon_selection.streaming_writer import (  # noqa: E402,F401
    write_jsonl_to_parquet,
)

from osm_polygon_selection.dataset_build.records import pbf_date_for as _pbf_date_for  # noqa: E402
from osm_polygon_selection.dataset_build.runner import run_build_dataset  # noqa: E402
from osm_polygon_selection.extract_status import extract_status as _extract_status  # noqa: E402
from osm_polygon_selection.git_meta import git_sha  # noqa: E402
from osm_polygon_selection.schema_defs import (  # noqa: E402
    build_schema as _build_package_schema,
    encode_geometry as _encode_pkg_geometry,
)


# Module-level helpers preserved for downstream tests that import
# ``scripts.build_dataset`` (e.g. characterization tests).


def extract_status(country: str) -> str:
    """Wrapper that points the package function at this script's PROC root."""
    return "clean" if _extract_status(PROC / country) else "killed"


def build_schema() -> pa.Schema:
    return _build_package_schema(geometry_encoding=GEOMETRY_ENCODING)


def _encode_geometry(row: dict) -> bytes | str | None:
    return _encode_pkg_geometry(row.get("geometry"), GEOMETRY_ENCODING)


_WHITELIST_CACHE: set[str] | None = None


def _load_whitelist() -> set[str]:
    """Load the 22,075-tag whitelist. Cached at module level."""
    global _WHITELIST_CACHE
    if _WHITELIST_CACHE is None:
        with RuntimeConfig.from_env().whitelist_path.open() as f:
            _WHITELIST_CACHE = set(json.load(f))
    return _WHITELIST_CACHE


def _load_whitelist_module_path() -> Path:
    return RuntimeConfig.from_env().whitelist_path


def row_to_record(row: dict, country: str, status: str, pbf_date: str) -> dict | None:
    """Thin wrapper around the package implementation."""
    from osm_polygon_selection.dataset_build.records import row_to_record as _row_to_record
    return _row_to_record(
        row,
        country=country,
        status=status,
        pbf_date=pbf_date,
        geometry_encoding=GEOMETRY_ENCODING,
        whitelist=_load_whitelist(),
    )


def pbf_date_for(country: str) -> str:
    """Thin wrapper around the package implementation."""
    return _pbf_date_for(country, raw_root=HDD / "raw")


def process_country(classified: Path, out_file: Path, country: str, status: str, pbf_date: str) -> int:
    """Thin wrapper around the streaming writer; returns polygon count.

    Used by ``run_build_dataset`` for the optimized per-country
    build path. The streaming writer vectorizes the matched_tag
    backfill; on exception the caller falls back to the per-row
    Python path using ``row_to_record``.
    """
    return write_jsonl_to_parquet(
        jsonl_path=classified,
        parquet_path=out_file,
        country=country,
        extract_status=status,
        pbf_date=pbf_date,
        geometry_encoding=GEOMETRY_ENCODING,
        whitelist_path=WHITELIST_PATH,
    )


def build_country_table(countries: list[dict]) -> str:
    """Thin wrapper for backwards-compat with downstream tests."""
    from osm_polygon_selection.country_table import (
        build_country_table as _package_build_country_table,
    )
    return _package_build_country_table(countries)


def write_readme(out_dir: Path, countries_done: list[dict], total_polygons: int) -> None:
    """Thin wrapper around the package function."""
    from osm_polygon_selection.readme import write_readme as _package_write_readme
    _package_write_readme(
        out_dir=out_dir,
        countries_done=countries_done,
        total_polygons=total_polygons,
        pipeline_version=PIPELINE_VERSION,
        git_sha_value=git_sha(),
        built_at=datetime.now().isoformat(),
        geometry_encoding=GEOMETRY_ENCODING,
    )


def main() -> None:
    run_build_dataset()


if __name__ == "__main__":
    main()

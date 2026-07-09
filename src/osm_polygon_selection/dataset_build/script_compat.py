"""Backwards-compat shims for ``scripts/build_dataset.py``.

The script module owns the env-var parsing + module-level
``HDD``/``PROC``/``GEOMETRY_ENCODING`` globals so characterization
tests can mutate them at import time. This module owns the
*implementation* of the legacy wrappers, which take a
:class:`ScriptConfig` to read those globals at call time.

The split is deliberate: tests that need to redirect lookups
mutate ``scripts.build_dataset.HDD`` etc.; the canonical
implementations in this module consult whichever config is
passed in (which the script wires up to its own module globals).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pyarrow as pa

from osm_polygon_selection.config import RuntimeConfig, git_sha
from osm_polygon_selection.dataset_build.records import pbf_date_for as _pbf_date_for
from osm_polygon_selection.readme.tables import build_country_table as _build_country_table
from osm_polygon_selection.readme.dataset import write_readme as _package_write_readme
from osm_polygon_selection.schema import build_schema as _build_package_schema
from osm_polygon_selection.schema import encode_geometry as _encode_pkg_geometry
from osm_polygon_selection.stages.status import extract_status as _extract_status


@dataclass
class ScriptConfig:
    """Holds the script-level globals this module reads at call time."""

    HDD: Path
    PROC: Path
    geometry_encoding: str = "wkt"


def make_config(HDD: Path, PROC: Path, geometry_encoding: str) -> ScriptConfig:
    return ScriptConfig(HDD=HDD, PROC=PROC, geometry_encoding=geometry_encoding)


def extract_status(cfg: ScriptConfig, country: str) -> str:
    """Wrapper that points the package function at this script's PROC root."""
    return _extract_status(cfg.PROC / country)


def build_schema(cfg: ScriptConfig) -> pa.Schema:
    return _build_package_schema(geometry_encoding=cfg.geometry_encoding)


def _encode_geometry(cfg: ScriptConfig, row: dict) -> bytes | str | None:
    return _encode_pkg_geometry(row.get("geometry"), cfg.geometry_encoding)


def _load_whitelist() -> set[str]:
    """Load the 22,075-tag whitelist. Cached at module level."""
    global _WHITELIST_CACHE
    if _WHITELIST_CACHE is None:
        with RuntimeConfig.from_env().whitelist_path.open() as f:
            _WHITELIST_CACHE = set(json.load(f))
    return _WHITELIST_CACHE


_WHITELIST_CACHE: set[str] | None = None


def _load_whitelist_module_path() -> Path:
    return RuntimeConfig.from_env().whitelist_path


def row_to_record(cfg: ScriptConfig, row: dict, country: str, status: str, pbf_date: str) -> dict | None:
    """Thin wrapper around the package implementation."""
    from osm_polygon_selection.dataset_build.records import row_to_record as _row_to_record
    return _row_to_record(
        row,
        country=country,
        status=status,
        pbf_date=pbf_date,
        geometry_encoding=cfg.geometry_encoding,
        whitelist=_load_whitelist(),
    )


def pbf_date_for(cfg: ScriptConfig, country: str) -> str:
    """Thin wrapper around the package implementation."""
    return _pbf_date_for(country, raw_root=cfg.HDD / "raw")


def process_country(
    cfg: ScriptConfig,
    classified: Path,
    out_file: Path,
    country: str,
    status: str,
    pbf_date: str,
    whitelist_path: Path,
) -> int:
    """Thin wrapper around the streaming writer; returns polygon count.

    Used by ``run_build_dataset`` for the optimized per-country
    build path. The streaming writer vectorizes the matched_tag
    backfill; on exception the caller falls back to the per-row
    Python path using ``row_to_record``.
    """
    from osm_polygon_selection.parquet_write.runner import write_jsonl_to_parquet
    return write_jsonl_to_parquet(
        jsonl_path=classified,
        parquet_path=out_file,
        country=country,
        extract_status=status,
        pbf_date=pbf_date,
        geometry_encoding=cfg.geometry_encoding,
        whitelist_path=whitelist_path,
    )


def build_country_table(_cfg: ScriptConfig, countries: list[dict]) -> str:
    """Thin wrapper for backwards-compat with downstream tests."""
    return _build_country_table(countries)


def write_readme(
    cfg: ScriptConfig,
    out_dir: Path,
    countries_done: list[dict],
    total_polygons: int,
    pipeline_version: str,
) -> None:
    """Thin wrapper around the package function."""
    _package_write_readme(
        out_dir=out_dir,
        countries_done=countries_done,
        total_polygons=total_polygons,
        pipeline_version=pipeline_version,
        git_sha_value=git_sha(),
        built_at=datetime.now().isoformat(),
        geometry_encoding=cfg.geometry_encoding,
    )


__all__ = [
    "ScriptConfig",
    "build_country_table",
    "build_schema",
    "extract_status",
    "make_config",
    "pbf_date_for",
    "process_country",
    "row_to_record",
    "write_readme",
]

"""Manifest row construction + final manifest writer.

Manifest rows are dicts of the form:
    {"country": str, "n_polygons": int, "extract_status": str, "pbf_date": str}

This module owns the three row factories (zero-yield, success,
killed-PBF) and the final manifest dict builder.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Mapping

from osm_polygon_selection.dataset_build.config import PIPELINE_VERSION
from osm_polygon_selection.git_meta import git_sha
from osm_polygon_selection.schema_defs import build_schema


def zero_yield_row(country: str, extract_status: str, pbf_date: str) -> dict:
    """Row for a country that ran but produced zero polygons."""
    return {
        "country": country,
        "n_polygons": 0,
        "extract_status": extract_status,
        "pbf_date": pbf_date,
    }


def success_row(country: str, n_polygons: int, extract_status: str, pbf_date: str) -> dict:
    """Row for a country that ran cleanly with at least one polygon."""
    return {
        "country": country,
        "n_polygons": n_polygons,
        "extract_status": extract_status,
        "pbf_date": pbf_date,
    }


def killed_pbf_row(country: str, pbf_mtime: float) -> dict:
    """Row for a country whose PBF is present but Stage 0 was killed."""
    return {
        "country": country,
        "n_polygons": 0,
        "extract_status": "killed",
        "pbf_date": datetime.fromtimestamp(pbf_mtime).strftime("%Y-%m-%d"),
    }


def build_manifest(
    countries_done: list[dict],
    total_polygons: int,
    *,
    schema: list[str],
) -> dict:
    """Build the final manifest.json dict (no I/O).

    The schema arg is accepted as a list of column names so the
    caller can pre-compute it once.
    """
    return {
        "version": PIPELINE_VERSION,
        "git_sha": git_sha(),
        "built_at": datetime.now().isoformat(),
        "total_polygons": total_polygons,
        "n_countries": sum(1 for c in countries_done if bool(c["n_polygons"])),
        "countries": countries_done,
        "schema": schema,
        "filters": {
            "min_area_km2": 0.1,
            "max_area_km2": 100.0,
            "whitelist_size": 22075,
        },
        "resources": {
            "blog_post": "https://noeflandre.com/posts/osm-data-analysis",
            "github_repo": "https://github.com/NoeFlandre/osm-polygon-selection",
            "related_repo": "https://github.com/NoeFlandre/osm-stats",
        },
    }


def write_manifest(manifest: Mapping, out_dir: Path) -> None:
    """Write manifest.json to the dataset root."""
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"manifest.json written")


def schema_columns(geometry_encoding: str) -> list[str]:
    """Return schema column names for the given geometry encoding."""
    return [f.name for f in build_schema(geometry_encoding=geometry_encoding)]

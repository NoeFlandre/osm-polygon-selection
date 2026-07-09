"""Regional sub-PBF batch processing for large countries.

Used for countries (france, germany) whose full PBF is too big
to process in a single interactive session. Geofabrik publishes
regional sub-PBFs (e.g. alsace, bretagne) that are 10-100x
smaller. This module orchestrates downloading + extracting
each region; each region writes to a per-region output file
so multiple regions can run in parallel.
"""

from __future__ import annotations

import os
from pathlib import Path

from osm_polygon_selection.config.paths import project_root
from osm_polygon_selection.operations.downloads import (
    build_curl_command,
    geofabrik_region_url,
    pbf_is_present,
    pbf_size_mb,
    region_pbf_name,
)
from osm_polygon_selection.operations.subprocesses import (
    build_stage0_command,
    env_with_data_root,
    run_with_env,
)


# Map of country -> [region names]. Subset of Geofabrik's
# per-country sub-regions.
COUNTRY_REGIONS: dict[str, list[str]] = {
    "france": [
        "alsace", "aquitaine", "auvergne", "basse-normandie", "bourgogne",
        "bretagne", "centre", "champagne-ardenne", "corse", "franche-comte",
        "guadeloupe", "guyane", "haute-normandie", "ile-de-france",
        "languedoc-roussillon", "limousin", "lorraine", "martinique",
        "mayotte", "midi-pyrenees", "nord-pas-de-calais", "pays-de-la-loire",
        "picardie", "poitou-charentes", "provence-alpes-cote-d-azur",
        "reunion", "rhone-alpes",
    ],
    "germany": [
        "baden-wuerttemberg", "bayern", "berlin", "brandenburg", "bremen",
        "hamburg", "hessen", "mecklenburg-vorpommern", "niedersachsen",
        "nordrhein-westfalen", "rheinland-pfalz", "saarland", "sachsen",
        "sachsen-anhalt", "schleswig-holstein", "thueringen",
    ],
}

DEFAULT_MAX_SECONDS = 600


def resolve_proj() -> Path:
    """Resolve the project root for subprocess ``cwd``."""
    return Path(os.environ.get("OSM_REPO_ROOT", project_root()))


def region_output_path(proc_dir: Path, country: str, region: str) -> Path:
    """Per-region 01_extracted_<region>.jsonl path."""
    country_dir = proc_dir / country
    country_dir.mkdir(parents=True, exist_ok=True)
    return country_dir / f"01_extracted_{region}.jsonl"


def download_region(
    *,
    region: str,
    country: str,
    raw_dir: Path,
    min_size_bytes: int = 1024 * 1024,
) -> Path:
    """Download a regional PBF if not already on disk."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    pbf = raw_dir / region_pbf_name(region)
    if pbf_is_present(pbf, min_size_bytes=min_size_bytes):
        return pbf
    url = geofabrik_region_url(country, region)
    cmd = build_curl_command(url, pbf)
    run_with_env(cmd, cwd=resolve_proj())
    return pbf


def extract_region(
    *,
    region: str,
    pbf: Path,
    country: str,
    proc_dir: Path,
    max_seconds: int = DEFAULT_MAX_SECONDS,
) -> int:
    """Run stage 0 on a regional PBF; returns polygon count."""
    out = region_output_path(proc_dir, country, region)
    cmd = build_stage0_command(pbf, out, max_seconds=max_seconds)
    run_with_env(cmd, cwd=resolve_proj())
    if not out.exists():
        return 0
    with out.open() as f:
        return sum(1 for _ in f)


def list_regions(country: str, only: list[str] | None = None) -> list[str]:
    """Return the regions to process for ``country``.

    If ``only`` is given, return that subset (after filtering to
    known regions). Otherwise return the full list from
    :data:`COUNTRY_REGIONS`.
    """
    full = COUNTRY_REGIONS[country]
    if only is None:
        return list(full)
    return [r for r in only if r in full]


__all__ = [
    "COUNTRY_REGIONS",
    "DEFAULT_MAX_SECONDS",
    "download_region",
    "extract_region",
    "list_regions",
    "region_output_path",
    "resolve_proj",
]

"""End-to-end build orchestration for the dataset pipeline.

The script (``scripts/build_dataset.py``) just calls
``run_build_dataset()`` after parsing env vars. This module
wires together the four focused modules:

- :mod:`discovery` — enumerate PROC + raw/ to find countries
- :mod:`country_processing` — per-country parquet writer
- :mod:`artifacts` — combined parquet + README + metadata + manifest
"""

from __future__ import annotations

import shutil
from pathlib import Path

from osm_polygon_selection.dataset_build.artifacts import write_final_artifacts
from osm_polygon_selection.dataset_build.config import (
    DATASET_DIR,
    GEOMETRY_ENCODING,
    HDD,
    PIPELINE_VERSION,
    PROC,
    WHITELIST_PATH,
)
from osm_polygon_selection.dataset_build.country_processing import (
    process_classified_country,
)
from osm_polygon_selection.dataset_build.discovery import (
    discover_killed_pbf_countries,
    iter_classified_country_dirs,
)


def run_build_dataset(out_dir: Path | None = None) -> Path:
    """End-to-end build: per-country parquets, combined, README, manifest.

    Returns the dataset root used.
    """
    out_dir = Path(out_dir) if out_dir is not None else DATASET_DIR
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    countries_done: list[dict] = []

    # First pass: 03_classified.jsonl countries.
    for country_dir in iter_classified_country_dirs(PROC):
        row = process_classified_country(
            country_dir,
            out_dir,
            geometry_encoding=GEOMETRY_ENCODING,
            whitelist_path=WHITELIST_PATH,
            raw_root=HDD / "raw",
        )
        if row is not None:
            countries_done.append(row)

    # Second pass: PBFs without 03 files.
    raw_dir = HDD / "raw"
    killed = discover_killed_pbf_countries(raw_dir, countries_done)
    for row in killed:
        print(f"  {row['country']}: 0 polygons (no 03 file, PBF present, recorded)")
    countries_done.extend(killed)

    print("\nBuilding combined parquet...")
    write_final_artifacts(
        out_dir,
        countries_done,
        pipeline_version=PIPELINE_VERSION,
        geometry_encoding=GEOMETRY_ENCODING,
    )
    return out_dir

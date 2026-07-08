"""End-to-end build orchestration for the dataset pipeline.

This is the new home of the body of ``scripts/build_dataset.py``'s
``main()``. The script now just parses env vars, sets module
constants, and calls ``run_build_dataset``.

Two passes over the filesystem:

1. Countries that produced a 03_classified.jsonl file. These
   produce per-country parquet files (via streaming writer, with
   fallback to per-row Python) and append a manifest row.
2. Countries that have a raw PBF but no 03 file at all (killed
   before Stage 2/3). Excludes the continent-wide "europe"
   parent and regional sub-PBFs of large countries.

After both passes, the combined parquet is written, then
README + metadata.yaml + manifest.json.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from osm_polygon_selection.dataset_build.combined import (
    combine_per_country_parquets as _combine_per_country_parquets,
)
from osm_polygon_selection.dataset_build.config import (
    DATASET_DIR,
    GEOMETRY_ENCODING,
    HDD,
    PIPELINE_VERSION,
    PROC,
    WHITELIST_PATH,
)
from osm_polygon_selection.dataset_build.countries import is_regional_child
from osm_polygon_selection.dataset_build.manifest import (
    build_manifest,
    killed_pbf_row,
    schema_columns,
    success_row,
    write_manifest,
    zero_yield_row,
)
from osm_polygon_selection.dataset_build.records import (
    pbf_date_for as _pbf_date_for,
)
from osm_polygon_selection.dataset_build.records import row_to_record
from osm_polygon_selection.extract_status import (
    extract_status as _extract_status,
)
from osm_polygon_selection.git_meta import git_sha
from osm_polygon_selection.readme import write_metadata_yaml, write_readme
from osm_polygon_selection.schema_defs import (
    build_schema as _build_package_schema,
)
from osm_polygon_selection.streaming_writer import write_jsonl_to_parquet
from osm_polygon_selection.runtime_config import RuntimeConfig as _RuntimeConfig

_WHITELIST_CACHE: set[str] | None = None


def _load_whitelist() -> set[str]:
    """Load the 22,075-tag whitelist. Cached at module level."""
    global _WHITELIST_CACHE
    if _WHITELIST_CACHE is None:
        with _RuntimeConfig.from_env().whitelist_path.open() as f:
            _WHITELIST_CACHE = set(json.load(f))
    return _WHITELIST_CACHE


def _process_classified_country(
    country_dir: Path,
    out_dir: Path,
    *,
    geometry_encoding: str,
    whitelist_path: Path,
) -> dict | None:
    """Run the per-country pipeline for one 03_classified.jsonl.

    Returns the manifest row (success or zero-yield).
    """
    country = country_dir.name
    classified = country_dir / "03_classified.jsonl"
    status = "clean" if _extract_status(country_dir) else "killed"
    pbf_date = _pbf_date_for(country, raw_root=HDD / "raw")

    out_file = out_dir / f"{country}.parquet"

    # Fast path: streaming writer (vectorized matched_tag backfill).
    try:
        n = write_jsonl_to_parquet(
            jsonl_path=classified,
            parquet_path=out_file,
            country=country,
            extract_status=status,
            pbf_date=pbf_date,
            geometry_encoding=geometry_encoding,
            whitelist_path=whitelist_path,
        )
    except Exception as e:
        print(f"  {country}: streaming writer failed ({e}); falling back to per-row path")
        n = 0

    if n > 0:
        print(f"  {country}: {n} polygons -> {out_file.name} (streaming)")
        return success_row(country, n, status, pbf_date)

    # Streaming path yielded zero OR failed → per-row fallback.
    if out_file.is_file():
        out_file.unlink()
    rows: list[dict] = []
    with classified.open() as f:
        for line in f:
            rec = row_to_record(
                json.loads(line),
                country=country,
                status=status,
                pbf_date=pbf_date,
                geometry_encoding=geometry_encoding,
                whitelist=_load_whitelist(),
            )
            if rec is not None:
                rows.append(rec)
    if not rows:
        # Zero-yield 03 file: extract ran but produced no polygons.
        print(f"  {country}: 0 polygons (zero-yield, recorded in manifest only)")
        return zero_yield_row(country, status, pbf_date)

    table = pa.Table.from_pylist(
        rows, schema=_build_package_schema(geometry_encoding=geometry_encoding)
    )
    pq.write_table(table, out_file, compression="snappy")
    print(f"  {country}: {len(rows)} polygons -> {out_file.name}")
    return success_row(country, len(rows), status, pbf_date)


def _discover_killed_pbf_countries(
    raw_dir: Path,
    countries_done: list[dict],
) -> list[dict]:
    """Find PBFs without a corresponding 03_classified.jsonl."""
    rows: list[dict] = []
    for pbf in sorted(raw_dir.glob("*-latest.osm.pbf")):
        country = pbf.name.replace("-latest.osm.pbf", "")
        if country == "europe":
            continue
        if is_regional_child(country):
            continue
        if any(c["country"] == country for c in countries_done):
            continue
        rows.append(killed_pbf_row(country, pbf.stat().st_mtime))
        print(f"  {country}: 0 polygons (no 03 file, PBF present, recorded)")
    return rows


def run_build_dataset(out_dir: Path | None = None) -> Path:
    """End-to-end build: parquets, combined, README, metadata, manifest.

    Returns the dataset root used.
    """
    out_dir = Path(out_dir) if out_dir is not None else DATASET_DIR
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    countries_done: list[dict] = []

    # First pass: 03_classified.jsonl countries.
    for country_dir in sorted(PROC.iterdir()):
        if not country_dir.is_dir():
            continue
        if country_dir.parent != PROC:
            continue
        classified = country_dir / "03_classified.jsonl"
        if not classified.exists():
            continue
        row = _process_classified_country(
            country_dir,
            out_dir,
            geometry_encoding=GEOMETRY_ENCODING,
            whitelist_path=WHITELIST_PATH,
        )
        if row is not None:
            countries_done.append(row)

    # Second pass: PBFs without 03 files.
    raw_dir = HDD / "raw"
    countries_done.extend(_discover_killed_pbf_countries(raw_dir, countries_done))

    print("\nBuilding combined parquet...")
    has_polygons = any(int(c.get("n_polygons", 0)) > 0 for c in countries_done)
    if has_polygons:
        total_rows = _combine_per_country_parquets(
            out_dir=out_dir,
            countries=countries_done,
            output_path=out_dir / "all_world.parquet",
        )
        print(f"  combined: {total_rows} polygons -> {out_dir / 'all_world.parquet'}")
    else:
        # No per-country parquets to combine (empty PROC, killed PBFs only).
        total_rows = 0
        print("  combined: skipped (no per-country parquets)")

    write_readme(
        out_dir=out_dir,
        countries_done=countries_done,
        total_polygons=total_rows,
        pipeline_version=PIPELINE_VERSION,
        git_sha_value=git_sha(),
        built_at=datetime.now().isoformat(),
        geometry_encoding=GEOMETRY_ENCODING,
    )
    write_metadata_yaml(out_dir)

    manifest = build_manifest(
        countries_done,
        total_rows,
        schema=schema_columns(GEOMETRY_ENCODING),
    )
    write_manifest(manifest, out_dir)
    return out_dir

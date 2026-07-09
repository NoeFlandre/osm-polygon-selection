"""Per-country processing for the build pipeline.

Owns ``process_classified_country``: turn one
``PROC/<country>/03_classified.jsonl`` into a per-country
parquet (and a manifest row). Uses the streaming writer as the
fast path and falls back to a per-row Python path on failure
or zero yield.
"""

from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from osm_polygon_selection.dataset_build.manifest import (
    success_row,
    zero_yield_row,
)
from osm_polygon_selection.dataset_build.records import (
    pbf_date_for as _pbf_date_for,
)
from osm_polygon_selection.dataset_build.records import row_to_record
from osm_polygon_selection.dataset_build.whitelist import load_whitelist
from osm_polygon_selection.stages.status import (
    extract_status as _extract_status,
)
from osm_polygon_selection.schema import (
    build_schema as _build_package_schema,
)
from osm_polygon_selection.parquet_write.runner import write_jsonl_to_parquet


def process_classified_country(
    country_dir: Path,
    out_dir: Path,
    *,
    geometry_encoding: str,
    whitelist_path: Path,
    raw_root: Path,
) -> dict | None:
    """Run the per-country pipeline for one 03_classified.jsonl.

    Returns the manifest row (success or zero-yield).
    """
    country = country_dir.name
    classified = country_dir / "03_classified.jsonl"
    status = "clean" if _extract_status(country_dir) else "killed"
    pbf_date = _pbf_date_for(country, raw_root=raw_root)

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
    whitelist = load_whitelist(whitelist_path)
    rows: list[dict] = []
    with classified.open() as f:
        for line in f:
            rec = row_to_record(
                json.loads(line),
                country=country,
                status=status,
                pbf_date=pbf_date,
                geometry_encoding=geometry_encoding,
                whitelist=whitelist,
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

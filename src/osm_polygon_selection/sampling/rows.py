"""Row emission and parquet lookup for the sampling pipeline.

Locates a country's parquet (per-country layout first, flat
layout fallback) and writes the sampled rows as JSONL.
"""

from __future__ import annotations

import json
from pathlib import Path


def find_country_parquet(ds_root: Path, country: str) -> Path | None:
    """Locate ``<country>.parquet`` under per_country/ or flat layout.

    Returns ``None`` if neither layout has the file.
    """
    pq_file = ds_root / "per_country" / country / f"{country}.parquet"
    if pq_file.exists():
        return pq_file
    pq_file = ds_root / f"{country}.parquet"
    if pq_file.exists():
        return pq_file
    return None


def tag_and_strip(row: dict, country: str) -> dict:
    """Tag the row's country and drop the (large) tags list.

    The sample JSONL only carries centroid + tags-free metadata; the
    full row is recoverable from the per-country parquet by osm_id.
    """
    row["country"] = country
    row.pop("tags", None)
    return row


def write_jsonl(rows: list[dict], out_path: Path) -> None:
    """Write the sampled rows as a newline-delimited JSON file."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

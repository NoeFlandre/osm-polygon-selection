"""Sample-row picker + per-country parquet lookup helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pyarrow.parquet as pq


def pick_sample_row(
    sample_path: Path,
    prefer_country: str = "liechtenstein",
    prefer_tag_prefix: str = "natural=",
) -> dict | None:
    """Pick one representative row from the sample JSONL.

    Returns the first row where ``country == prefer_country`` AND
    ``matched_tag`` starts with ``prefer_tag_prefix``. Falls back
    to the first row of the requested country, then to the very
    first row in the file. Returns ``None`` if the file is empty
    or missing.
    """
    if not sample_path.is_file():
        return None
    first_row: dict | None = None
    country_fallback: dict | None = None
    with sample_path.open() as f:
        for line in f:
            row = json.loads(line)
            if first_row is None:
                first_row = row
            if row.get("country") == prefer_country:
                if country_fallback is None:
                    country_fallback = row
                if (row.get("matched_tag") or "").startswith(prefer_tag_prefix):
                    return row
    return country_fallback or first_row


def fetch_full_row_from_parquet(parquet_path: Path, osm_id: int) -> dict | None:
    """Look up ``osm_id`` in a per-country parquet and return the row."""
    if not parquet_path.is_file():
        return None
    try:
        t = pq.read_table(parquet_path, filters=[("osm_id", "=", int(osm_id))])
    except Exception:
        return None
    if t.num_rows == 0:
        return None
    rec = t.to_pylist()[0]
    if rec.get("tags") is not None:
        rec["tags"] = [str(x) for x in rec["tags"]]
    return rec


__all__ = ["fetch_full_row_from_parquet", "pick_sample_row"]

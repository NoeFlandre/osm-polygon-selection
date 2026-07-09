"""JSONL row loading and centroid extraction for the visualizer.

Two centroid formats are accepted:

- ``centroid_lon`` + ``centroid_lat`` (parquet-derived rows)
- ``centroid = [lon, lat]`` (legacy JSONL rows)

Rows without any coordinates are skipped (not plotted).
"""

from __future__ import annotations

import json
from pathlib import Path


def load_rows(jsonl_path: Path, limit: int) -> list[dict]:
    """Read at most ``limit`` rows from the JSONL file."""
    rows: list[dict] = []
    with jsonl_path.open() as f:
        for line in f:
            rows.append(json.loads(line))
            if len(rows) >= limit:
                break
    return rows


def extract_centroid(row: dict) -> tuple[float, float] | None:
    """Return ``(lon, lat)`` for a row or None if no coordinates.

    Accepts both flat ``centroid_lon``/``centroid_lat`` and nested
    ``centroid = [lon, lat]``. Returns None if neither is present
    or any coordinate is None.
    """
    if "centroid_lon" in row and "centroid_lat" in row:
        lon, lat = row["centroid_lon"], row["centroid_lat"]
    elif "centroid" in row:
        lon, lat = row["centroid"]
    else:
        return None
    if lon is None or lat is None:
        return None
    return float(lon), float(lat)


def collect_countries(rows: list[dict]) -> set[str]:
    """Return the set of non-empty country values across rows."""
    return {
        r["country"]
        for r in rows
        if "country" in r and r["country"]
    }


__all__ = ["collect_countries", "extract_centroid", "load_rows"]

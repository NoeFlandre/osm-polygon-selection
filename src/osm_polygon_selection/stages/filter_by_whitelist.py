"""Filter a polygon JSONL by intersection with the OSM tag whitelist.

A polygon survives if at least one of its tags is in the whitelist
(i.e. it has been tagged with at least one landuse/landcover-relevant
key=value pair).
"""

import json
from pathlib import Path

from osm_polygon_selection.core.jsonl_utils import stream_jsonl


def filter_polygons(
    jsonl_in: Path, whitelist_path: Path, jsonl_out: Path,
) -> tuple[int, int]:
    """Stream polygons in, write those whose tags intersect the whitelist.

    Returns (kept_count, dropped_count).
    """
    with whitelist_path.open() as f:
        whitelist = set(json.load(f))

    def transform(row: dict) -> dict | None:
        if set(row["tags"]) & whitelist:
            return row
        return None

    kept, seen = stream_jsonl(jsonl_in, jsonl_out, transform)
    return kept, seen - kept

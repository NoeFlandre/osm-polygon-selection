"""Filter a polygon JSONL by intersection with the OSM tag whitelist.

A polygon survives if at least one of its tags is in the whitelist
(i.e. it has been tagged with at least one landuse/landcover-relevant
key=value pair).
"""

import json
from pathlib import Path


def filter_polygons(
    jsonl_in: Path, whitelist_path: Path, jsonl_out: Path,
) -> tuple[int, int]:
    """Stream polygons in, write those whose tags intersect the whitelist.

    Returns (kept_count, dropped_count).
    """
    with whitelist_path.open() as f:
        whitelist = set(json.load(f))

    kept = 0
    dropped = 0
    jsonl_out.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_in.open() as f, jsonl_out.open("w") as out:
        for line in f:
            row = json.loads(line)
            if set(row["tags"]) & whitelist:
                out.write(json.dumps(row) + "\n")
                kept += 1
            else:
                dropped += 1
    return kept, dropped

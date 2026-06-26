"""Entry point: PBF -> JSONL of polygons.

Resumable + stoppable: pass --limit N to cap the run, then re-run
with no --limit (or a higher N) to continue from the WAL.
"""

import argparse
from pathlib import Path

from osm_polygon_selection.stages.extract import extract


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pbf", type=Path, help="Path to .osm.pbf file")
    parser.add_argument("out", type=Path, help="Path to output .jsonl file")
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Stop after this many NEW polygons in this run",
    )
    args = parser.parse_args()
    n = extract(args.pbf, args.out, limit=args.limit)
    print(f"Wrote {n} polygons to {args.out}")


if __name__ == "__main__":
    main()

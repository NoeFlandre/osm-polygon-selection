"""Entry point: PBF -> JSONL of polygons"""

import argparse
from pathlib import Path

from osm_polygon_selection.stages.extract import extract


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pbf", type=Path, help="Path to .osm.pbf file")
    parser.add_argument("out", type=Path, help="Path to the output file")
    args = parser.parse_args()
    n = extract(args.pbf, args.out)
    print(f"Wrote {n} polygons to {args.out}")


if __name__ == "__main__":
    main()

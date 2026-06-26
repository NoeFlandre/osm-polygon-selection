"""Stage 4: attach continent to each polygon via spatial lookup."""

import argparse
from pathlib import Path

from osm_polygon_selection.stages.classify import classify_jsonl, size_bin


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl_in", type=Path, help="Filtered polygons JSONL")
    parser.add_argument(
        "shp", type=Path,
        help="Path to Natural Earth admin0 .shp file",
    )
    parser.add_argument("jsonl_out", type=Path, help="Output JSONL")
    args = parser.parse_args()
    n = classify_jsonl(args.jsonl_in, args.shp, args.jsonl_out)
    print(f"wrote {n} polygons to {args.jsonl_out}")


if __name__ == "__main__":
    main()

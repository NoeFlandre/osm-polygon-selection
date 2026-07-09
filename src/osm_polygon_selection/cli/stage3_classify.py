"""Stage 3 CLI: attach continent to each polygon via spatial lookup."""

from __future__ import annotations

import argparse
from pathlib import Path

from osm_polygon_selection.stages.classify import classify_jsonl


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl_in", type=Path, help="Filtered polygons JSONL")
    parser.add_argument(
        "shp", type=Path,
        help="Path to Natural Earth admin0 .shp file",
    )
    parser.add_argument("jsonl_out", type=Path, help="Output JSONL")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    n = classify_jsonl(args.jsonl_in, args.shp, args.jsonl_out)
    print(f"wrote {n} polygons to {args.jsonl_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

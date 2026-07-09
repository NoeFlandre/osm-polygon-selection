"""Stage 2 CLI: filter a polygon JSONL by the OSM tag whitelist."""

from __future__ import annotations

import argparse
from pathlib import Path

from osm_polygon_selection.stages.filter_by_whitelist import filter_polygons


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl_in", type=Path, help="Input polygon JSONL")
    parser.add_argument("whitelist", type=Path, help="Whitelist JSON file")
    parser.add_argument("jsonl_out", type=Path, help="Output filtered JSONL")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    kept, dropped = filter_polygons(args.jsonl_in, args.whitelist, args.jsonl_out)
    total = kept + dropped
    pct = 100.0 * kept / total if total else 0.0
    print(f"kept {kept}/{total} ({pct:.1f}%), dropped {dropped}, wrote {args.jsonl_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

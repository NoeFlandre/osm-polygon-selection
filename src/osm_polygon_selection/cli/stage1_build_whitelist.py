"""Stage 1 CLI: build the OSM tag whitelist from osm-stats outputs."""

from __future__ import annotations

import argparse
from pathlib import Path

from osm_polygon_selection.stages.whitelist import load_whitelist


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "osm_stats_root", type=Path,
        help="Path to dir containing tfidf/ and embeddings/ subdirs",
    )
    parser.add_argument(
        "out", type=Path,
        help="Path to output JSON file (list of 'key=value' strings)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    tags = load_whitelist(args.osm_stats_root, out_path=args.out)
    print(f"wrote {len(tags)} unique tags to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

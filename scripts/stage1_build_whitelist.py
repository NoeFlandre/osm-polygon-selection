"""Build the OSM tag whitelist from osm-stats outputs."""

import argparse
from pathlib import Path

from osm_polygon_selection.whitelist import load_whitelist


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "osm_stats_root", type=Path,
        help="Path to dir containing tfidf/ and embeddings/ subdirs",
    )
    parser.add_argument(
        "out", type=Path,
        help="Path to output JSON file (list of 'key=value' strings)",
    )
    args = parser.parse_args()
    tags = load_whitelist(args.osm_stats_root, out_path=args.out)
    print(f"wrote {len(tags)} unique tags to {args.out}")


if __name__ == "__main__":
    main()

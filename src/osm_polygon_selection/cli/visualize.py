"""Visualize CLI: build a folium preview map of a parquet sample."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from osm_polygon_selection.visualization.render import render_map


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parquet", type=Path, help="Path to sample parquet")
    parser.add_argument(
        "out_html", type=Path, nargs="?",
        help="Output HTML path (default: <parquet_stem>.html)",
    )
    parser.add_argument(
        "--limit", type=int, default=20_000,
        help="Max polygons to include in the map (default 20,000)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out_html: Optional[Path] = args.out_html
    if out_html is None:
        out_html = args.parquet.with_suffix(".html")
    render_map(args.parquet, out_html, limit=args.limit)
    print(f"wrote {out_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

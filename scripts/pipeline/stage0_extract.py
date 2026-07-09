"""Thin entry point: PBF -> JSONL of polygons.

Thin wrapper around :mod:`osm_polygon_selection.cli.stage0_extract`.
"""

from osm_polygon_selection.cli.stage0_extract import main, build_parser

__all__ = ["build_parser", "main"]


if __name__ == "__main__":
    raise SystemExit(main())

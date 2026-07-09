"""Thin entry point: filter a polygon JSONL by the OSM tag whitelist.

Thin wrapper around :mod:`osm_polygon_selection.cli.stage2_filter`.
"""

from osm_polygon_selection.cli.stage2_filter import main, build_parser

__all__ = ["build_parser", "main"]


if __name__ == "__main__":
    raise SystemExit(main())

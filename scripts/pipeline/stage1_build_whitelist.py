"""Thin entry point: build the OSM tag whitelist from osm-stats outputs.

Thin wrapper around :mod:`osm_polygon_selection.cli.stage1_build_whitelist`.
"""

from osm_polygon_selection.cli.stage1_build_whitelist import main, build_parser

__all__ = ["build_parser", "main"]


if __name__ == "__main__":
    raise SystemExit(main())

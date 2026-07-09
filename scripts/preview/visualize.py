"""Thin entry point: build a folium preview map of a parquet sample.

Thin wrapper around :mod:`osm_polygon_selection.cli.visualize`.
"""

from osm_polygon_selection.cli.visualize import main, build_parser

__all__ = ["build_parser", "main"]


if __name__ == "__main__":
    raise SystemExit(main())

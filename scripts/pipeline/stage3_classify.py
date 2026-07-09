"""Thin entry point: attach continent to each polygon via spatial lookup.

Thin wrapper around :mod:`osm_polygon_selection.cli.stage3_classify`.
"""

from osm_polygon_selection.cli.stage3_classify import main, build_parser

__all__ = ["build_parser", "main"]


if __name__ == "__main__":
    raise SystemExit(main())

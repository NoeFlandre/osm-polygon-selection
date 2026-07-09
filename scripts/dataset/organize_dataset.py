"""Thin entry point: move/rename dataset files into the canonical layout.

Thin wrapper around :mod:`osm_polygon_selection.cli.organize_dataset`.
"""

from osm_polygon_selection.cli.organize_dataset import main, build_parser

__all__ = ["build_parser", "main"]


if __name__ == "__main__":
    main()

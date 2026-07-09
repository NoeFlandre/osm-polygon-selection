"""Thin entry point: upload a dataset directory to HuggingFace.

Thin wrapper around :mod:`osm_polygon_selection.cli.upload_to_hf`.
"""

from osm_polygon_selection.cli.upload_to_hf import main, build_parser

__all__ = ["build_parser", "main"]


if __name__ == "__main__":
    raise SystemExit(main())

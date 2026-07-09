"""Thin entry point: write train/val/test parquet files for the HF viewer.

Thin wrapper around :mod:`osm_polygon_selection.cli.split_parquets`.
"""

from osm_polygon_selection.cli.split_parquets import main, build_parser

__all__ = ["build_parser", "main"]


if __name__ == "__main__":
    raise SystemExit(main())

"""Process all European countries end-to-end.

Thin wrapper around :func:`osm_polygon_selection.operations.cli.run_europe`.
"""

from osm_polygon_selection.operations.cli import (
    build_run_europe_parser, run_europe,
)

__all__ = ["build_run_europe_parser", "run_europe"]

if __name__ == "__main__":
    raise SystemExit(run_europe())

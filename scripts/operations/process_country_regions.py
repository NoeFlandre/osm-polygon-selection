"""Process a country by downloading and extracting regional sub-PBFs.

Thin wrapper around :func:`osm_polygon_selection.operations.cli.process_regions`.
"""

from osm_polygon_selection.operations.cli import (
    build_process_regions_parser, process_regions,
)

__all__ = ["build_process_regions_parser", "process_regions"]

if __name__ == "__main__":
    raise SystemExit(process_regions())

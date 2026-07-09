"""Thin entry point: build a small parquet sample for folium previewing.

Thin wrapper around :mod:`osm_polygon_selection.cli.sample_for_map`.

Re-exports ``power_law_alloc``, ``grid_sample_country``, and the
``FLOOR`` / ``CAP`` / ``POWER`` / ``GEO_COLS`` / ``ALL_COLS``
constants for backwards-compat with tests that import them from
the script.
"""

from __future__ import annotations

import pyarrow.parquet as pq  # noqa: F401 (re-exported)

from osm_polygon_selection.cli.sample_for_map import (  # noqa: F401
    PROCESSED_ROOT,
    main,
)
from osm_polygon_selection.config.paths import dataset_root  # noqa: F401 (re-exported)
from osm_polygon_selection.sampling import (  # noqa: F401
    ALL_COLS,
    CAP,
    DEFAULT_OUT_PATH,
    FLOOR,
    GEO_COLS,
    POWER,
    grid_sample_country,
    power_law_alloc,
    run_sample_for_map,
)

DATASET_ROOT = dataset_root()

__all__ = [
    "ALL_COLS",
    "CAP",
    "DATASET_ROOT",
    "DEFAULT_OUT_PATH",
    "FLOOR",
    "GEO_COLS",
    "POWER",
    "PROCESSED_ROOT",
    "grid_sample_country",
    "main",
    "pq",
    "power_law_alloc",
    "run_sample_for_map",
]


if __name__ == "__main__":
    main()

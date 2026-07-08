"""Thin CLI for the dataset sample-for-map pipeline.

Delegates to ``osm_polygon_selection.sampling.runner.run_sample_for_map``.

Re-exports ``power_law_alloc``, ``grid_sample_country``, and the
``FLOOR`` / ``CAP`` / ``POWER`` / ``GEO_COLS`` / ``ALL_COLS``
constants for backwards-compat with tests that import them
from the script.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pyarrow.parquet as pq  # noqa: F401 (re-exported)

from osm_polygon_selection.paths import dataset_root
from osm_polygon_selection.runtime_config import RuntimeConfig
from osm_polygon_selection.sampling import (
    ALL_COLS,  # noqa: F401
    CAP,  # noqa: F401
    DEFAULT_OUT_PATH,
    FLOOR,  # noqa: F401
    GEO_COLS,  # noqa: F401
    POWER,  # noqa: F401
    grid_sample_country,
    power_law_alloc,
    run_sample_for_map,
)

PROCESSED_ROOT = RuntimeConfig.from_env().processed_root
DATASET_ROOT = dataset_root()  # noqa: F401 (re-exported)
OUT_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT_PATH


def main() -> None:
    run_sample_for_map(PROCESSED_ROOT, out_path=OUT_PATH)


if __name__ == "__main__":
    main()



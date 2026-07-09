"""Backwards-compat launcher for ``scripts/dataset/sample_for_map.py``.

Re-exports the sampling-package symbols
(``power_law_alloc``, ``grid_sample_country``, the
``FLOOR``/``CAP``/``POWER``/``GEO_COLS``/``ALL_COLS``
constants, and ``pyarrow.parquet as pq``) for tests that import
them from the script path.
"""

from __future__ import annotations

import runpy
from pathlib import Path

import pyarrow.parquet as pq  # noqa: F401

from scripts.dataset.sample_for_map import (  # noqa: F401
    ALL_COLS, CAP, DATASET_ROOT, DEFAULT_OUT_PATH, FLOOR, GEO_COLS,
    POWER, PROCESSED_ROOT, grid_sample_country, main, power_law_alloc,
    run_sample_for_map,
)

if __name__ == "__main__":
    runpy.run_path(
        str(Path(__file__).resolve().parent / "dataset" / "sample_for_map.py"),
        run_name="__main__",
    )

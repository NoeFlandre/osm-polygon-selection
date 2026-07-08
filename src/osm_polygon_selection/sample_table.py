"""Sample-table renderers (backwards-compat facade).

The implementation lives in :mod:`osm_polygon_selection.sample_tables`.
This module re-exports the public functions so existing imports
keep working.
"""

from __future__ import annotations

from osm_polygon_selection.sample_tables import (  # noqa: F401
    SIZE_BIN_ORDER,
    build_example_row_table,
    build_size_bin_distribution_table,
    compute_global_size_bin_distribution,
    compute_sample_size_bin_distribution,
    fetch_full_row_from_parquet,
    pick_sample_row,
    truncate,
)

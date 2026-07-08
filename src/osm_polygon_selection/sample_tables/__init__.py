"""Sample-table renderers used by the dataset README.

Modules:
  distribution  - size-bin distribution (sample + global)
  formatting    - markdown rendering helpers (truncate, distribution table)
  lookup        - sample-row picker + per-country parquet lookup
  example_row   - full-row example table renderer
"""

from osm_polygon_selection.sample_tables.distribution import (
    SIZE_BIN_ORDER,
    compute_global_size_bin_distribution,
    compute_sample_size_bin_distribution,
)
from osm_polygon_selection.sample_tables.example_row import (
    build_example_row_table,
)
from osm_polygon_selection.sample_tables.formatting import (
    build_size_bin_distribution_table,
    truncate,
)
from osm_polygon_selection.sample_tables.lookup import (
    fetch_full_row_from_parquet,
    pick_sample_row,
)

__all__ = [
    "SIZE_BIN_ORDER",
    "build_example_row_table",
    "build_size_bin_distribution_table",
    "compute_global_size_bin_distribution",
    "compute_sample_size_bin_distribution",
    "fetch_full_row_from_parquet",
    "pick_sample_row",
    "truncate",
]

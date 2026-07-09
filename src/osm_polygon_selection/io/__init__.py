"""I/O helpers: file loaders, pyarrow wrappers, whitelist reading.

Canonical location for low-level data loading and pyarrow compute
shims.

Modules:

- :mod:`whitelist` — load/compute whitelist membership.
- :mod:`pyarrow_compat` — typed wrappers for ``pyarrow.compute``
  functions missing from the type stubs.
"""

from osm_polygon_selection.io.whitelist import (
    DEFAULT_WHITELIST_PATH,
    clear_whitelist_cache,
    compute_matched_tag,
    load_whitelist,
    vectorized_compute_matched_tags,
)

__all__ = [
    "DEFAULT_WHITELIST_PATH",
    "clear_whitelist_cache",
    "compute_matched_tag",
    "load_whitelist",
    "vectorized_compute_matched_tags",
]

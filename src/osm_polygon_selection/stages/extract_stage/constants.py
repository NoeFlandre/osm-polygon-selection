"""Stage 0 tunable constants.

Centralized so call sites don't reach into module globals.
"""

from __future__ import annotations

# Hard upper bounds on what we'll attempt to validate. These exist to
# prevent a single pathological multipolygon (e.g. one with thousands
# of self-intersecting rings, which some European countries have) from
# blocking the entire extract for hours in shapely's make_valid or
# is_valid.
#
# Country-level observations that motivated these limits:
#   - italy: stuck on a single multipolygon > 25 min, no polygons yielded
#   - poland: stuck on a single multipolygon > 20 min
#   - spain: similar pattern, eventually yielded but slowly
#   - france: stuck in first-pass index build for 30+ min before any
#             yield; size suggests the offending relation is enormous
#   - germany: same as france
#
# We drop polygons that are too complex rather than processing them.
MIN_AREA_KM2 = 0.1
MAX_AREA_KM2 = 100.0

MAX_VERTICES = 50_000      # total coord count across all rings
MAX_GEOMETRY_BYTES = 10 * 1024 * 1024  # 10MB WKT safety cap
# Per-polygon timeout for make_valid / is_valid (seconds).
VALIDATION_TIMEOUT_S = 5

# Progress file cadence.
PROGRESS_INTERVAL_S = 15.0
FIRST_PROGRESS_AFTER = 100

# WAL cadence. Flush every N writes to avoid millions of disk syncs.
WAL_BATCH = 10_000

# File suffixes (sibling-of-output paths).
WAL_SUFFIX = ".seen_ids"
PROGRESS_SUFFIX = ".progress.json"
LOG_SUFFIX = ".run.json"

__all__ = [
    "FIRST_PROGRESS_AFTER",
    "LOG_SUFFIX",
    "MAX_AREA_KM2",
    "MAX_GEOMETRY_BYTES",
    "MAX_VERTICES",
    "MIN_AREA_KM2",
    "PROGRESS_INTERVAL_S",
    "PROGRESS_SUFFIX",
    "VALIDATION_TIMEOUT_S",
    "WAL_BATCH",
    "WAL_SUFFIX",
]

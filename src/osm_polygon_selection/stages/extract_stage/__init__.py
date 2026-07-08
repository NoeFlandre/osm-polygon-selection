"""Stage 0 (extract) package.

Owns the streaming PBF -> JSONL pipeline:

  extract_stage.constants  - magic numbers and suffix strings
  extract_stage.timeout    - SIGALRM-based per-polygon validation cap
  extract_stage.progress   - .progress.json writer + helpers
  extract_stage.wal        - .seen_ids write-ahead log
  extract_stage.records    - _record / _record_from_wkt
  extract_stage.run_log    - .run.json finalizer
  extract_stage.runner     - extract() orchestration

``stages.extract`` re-exports the public ``extract`` function and
the constants so existing callers and tests keep working.
"""

from osm_polygon_selection.stages.extract_stage.constants import (
    FIRST_PROGRESS_AFTER,
    LOG_SUFFIX,
    MAX_AREA_KM2,
    MAX_GEOMETRY_BYTES,
    MAX_VERTICES,
    MIN_AREA_KM2,
    PROGRESS_INTERVAL_S,
    PROGRESS_SUFFIX,
    VALIDATION_TIMEOUT_S,
    WAL_BATCH,
    WAL_SUFFIX,
)
from osm_polygon_selection.stages.extract_stage.records import (
    ValidationTimeout,
    record_from_wkt,
)
from osm_polygon_selection.stages.extract_stage.runner import extract

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
    "ValidationTimeout",
    "extract",
    "record_from_wkt",
]

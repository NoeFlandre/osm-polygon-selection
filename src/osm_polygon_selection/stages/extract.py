"""Stage 0 (extract) facade.

Owns nothing itself; re-exports the public symbols from
:mod:`osm_polygon_selection.stages.extract_stage` so existing
imports (``from osm_polygon_selection.stages.extract import extract``)
keep working.

Legacy aliases ``_record`` and ``_record_from_wkt`` are preserved
for backwards-compat with tests that monkeypatch the in-module
symbols. The ``osmium`` symbol is also re-exported so tests can
patch ``osm_polygon_selection.stages.extract.osmium.FileProcessor``.
"""

from __future__ import annotations

import osmium  # noqa: F401  (re-exported for legacy test patches)

from osm_polygon_selection.stages.extract_stage import (  # noqa: F401
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
    ValidationTimeout,
    extract,
    record_from_wkt,
)
from osm_polygon_selection.stages.extract_stage.records import (
    record as _record,
    record_from_wkt as _record_from_wkt,
)

# Module-level aliases for tests that monkeypatch the in-module
# ``_record`` symbol. Kept here (not in extract_stage) so the
# patch is local to ``osm_polygon_selection.stages.extract``.
_record = _record
_record_from_wkt = _record_from_wkt

"""Build-time configuration: env vars, paths, geometry encoding.

Centralises every environment-driven knob the build pipeline reads.
Callers (the script or runner) read attributes off this module to
avoid re-parsing the env on every call.
"""

from __future__ import annotations

import os
from pathlib import Path

from osm_polygon_selection.paths import dataset_root
from osm_polygon_selection.runtime_config import RuntimeConfig

PIPELINE_VERSION: str = "v0.1.0"

_runtime_config: RuntimeConfig = RuntimeConfig.from_env()
HDD: Path = _runtime_config.data_root
PROC: Path = _runtime_config.processed_root
DATASET_DIR: Path = dataset_root()  # honors $OSM_DATASET_DIR
WHITELIST_PATH: Path = _runtime_config.whitelist_path

# Geometry encoding: wkt (default, text), wkb (binary, ~50% smaller),
# or none (drop entirely, just keep centroid + area).
_GEOMETRY_ENCODING: str = os.environ.get("OSM_POLYGON_GEOMETRY", "wkt").lower()
if _GEOMETRY_ENCODING not in ("wkt", "wkb", "none"):
    raise SystemExit(
        f"OSM_POLYGON_GEOMETRY must be wkt, wkb, or none; got {_GEOMETRY_ENCODING!r}"
    )
GEOMETRY_ENCODING: str = _GEOMETRY_ENCODING

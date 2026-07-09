"""Build-dataset CLI: parse env vars, expose config knobs, run the build.

This module is the canonical owner of the ``OSM_POLYGON_GEOMETRY``
env-var validation and the public ``main()`` entry point that
delegates to ``dataset_build.runner.run_build_dataset``.

Module-level paths (``HDD`` / ``PROC`` / ``DATASET_DIR``) and
legacy wrappers (``row_to_record`` / ``pbf_date_for`` /
``build_country_table`` / ``write_readme`` / ``process_country``)
are kept here as the canonical implementation. The
:file:`scripts/build_dataset.py` thin wrapper simply re-exports
them; characterization tests can still mutate ``scripts.build_dataset.HDD``
to redirect lookups during tests (the wrappers there resolve
through ``scripts.build_dataset`` module globals via runtime
binding).

Format controlled by ``OSM_POLYGON_GEOMETRY``:

  ``wkt``    (default) — keep geometry as WKT (text)
  ``wkb``              — keep geometry as WKB (binary, ~50% smaller)
  ``none``             — drop geometry (centroid + area only)
"""

from __future__ import annotations

import os
from pathlib import Path

# Env-var parsing at import time so the validation runs on first
# import. Imports of the package come after the env-var check.
_GEOMETRY_ENCODING = os.environ.get("OSM_POLYGON_GEOMETRY", "wkt").lower()
if _GEOMETRY_ENCODING not in ("wkt", "wkb", "none"):
    raise SystemExit(
        f"OSM_POLYGON_GEOMETRY must be wkt, wkb, or none; got {_GEOMETRY_ENCODING!r}"
    )
GEOMETRY_ENCODING: str = _GEOMETRY_ENCODING

from osm_polygon_selection.config import RuntimeConfig  # noqa: E402
from osm_polygon_selection.config.paths import dataset_root  # noqa: E402
from osm_polygon_selection.dataset_build.config import (  # noqa: E402,F401
    PIPELINE_VERSION,
    WHITELIST_PATH,
)
from osm_polygon_selection.dataset_build.runner import run_build_dataset  # noqa: E402

_RUNTIME_CONFIG = RuntimeConfig.from_env()
HDD: Path = _RUNTIME_CONFIG.data_root
PROC: Path = _RUNTIME_CONFIG.processed_root
DATASET_DIR: Path = dataset_root()  # honors $OSM_DATASET_DIR


def main() -> None:
    run_build_dataset()


__all__ = [
    "DATASET_DIR",
    "GEOMETRY_ENCODING",
    "HDD",
    "PIPELINE_VERSION",
    "PROC",
    "WHITELIST_PATH",
    "main",
]


if __name__ == "__main__":
    main()

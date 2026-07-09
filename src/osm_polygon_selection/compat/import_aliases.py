"""Public backwards-compatibility import aliases.

This module is the single source of truth for legacy
``osm_polygon_selection.<old>`` -> canonical subpackage mappings.
Two installation strategies are used together so the aliases
work whether or not the user first imports the parent package:

1. ``sys.modules`` pre-population when the package is imported
   (covers ``import osm_polygon_selection; from osm_polygon_selection.<old> import ...``).
2. PEP 562 module-level ``__getattr__`` on the package, which
   triggers on direct ``import osm_polygon_selection.<old>``
   even without the parent import.

Both strategies map the same set of legacy paths.
"""

from __future__ import annotations

import importlib
import sys
from typing import Any


# Canonical (target) module path for each legacy root-level alias.
LEGACY_ALIASES: dict[str, str] = {
    "country_table": "osm_polygon_selection.readme.tables",
    "extract_status": "osm_polygon_selection.stages.status",
    "git_meta": "osm_polygon_selection.config.git",
    "paths": "osm_polygon_selection.config.paths",
    "pyarrow_compat": "osm_polygon_selection.io.pyarrow_compat",
    "runtime_config": "osm_polygon_selection.config.runtime",
    "whitelist_io": "osm_polygon_selection.io.whitelist",
    "schema_defs": "osm_polygon_selection.schema",
    "sample_table": "osm_polygon_selection.sample_tables",
    "readme_render": "osm_polygon_selection.readme",
    "regional_pbf_meta": "osm_polygon_selection.pbf_meta.regional",
    "streaming_writer": "osm_polygon_selection.parquet_write.runner",
}


def _resolve_legacy(name: str) -> Any:
    """Resolve a legacy root-level name to the canonical module."""
    target = LEGACY_ALIASES.get(name)
    if target is None:
        raise AttributeError(f"module 'osm_polygon_selection' has no attribute {name!r}")
    return importlib.import_module(target)


def install_sys_modules_aliases() -> None:
    """Pre-populate ``sys.modules`` for each legacy alias.

    Idempotent: skips names that are already in ``sys.modules``
    (which would mean either the facade file still exists, or
    a prior import resolved it).
    """
    for old_name, canonical in LEGACY_ALIASES.items():
        old_path = f"osm_polygon_selection.{old_name}"
        if old_path in sys.modules:
            continue
        try:
            module = importlib.import_module(canonical)
        except ImportError:
            continue
        sys.modules[old_path] = module


# PEP 562: package-level __getattr__ triggers when a submodule
# is not in sys.modules and not found by the normal lookup
# machinery. This handles ``import osm_polygon_selection.<old>``
# even when the parent package was not imported first.
def __getattr__(name: str) -> Any:
    if name in LEGACY_ALIASES:
        module = _resolve_legacy(name)
        sys.modules[f"osm_polygon_selection.{name}"] = module
        return module
    raise AttributeError(f"module 'osm_polygon_selection' has no attribute {name!r}")


__all__ = ["LEGACY_ALIASES", "install_sys_modules_aliases"]


# Install the sys.modules aliases at module-load time so that
# ``import osm_polygon_selection`` and any subsequent
# ``from osm_polygon_selection.<old> import ...`` see them.
install_sys_modules_aliases()

"""Runtime filesystem configuration: where data lives at runtime.

Centralizes the paths used by the build / sample / split / upload
pipeline so scripts don't hard-code machine locations.

Environment variables:

- ``OSM_DATA_ROOT``: umbrella directory containing ``processed/``,
  ``raw/``, ``dataset/``, ``whitelist.json``. Default:
  ``/Volumes/Seagate M3/osm-polygon-selection``.
- ``OSM_DATASET_DIR``: override only the dataset subdirectory. Useful
  for publishing to a different folder name (e.g. a snapshot copy).
  Default: ``$OSM_DATA_ROOT/dataset``.

Importing this module does NOT touch the filesystem — only the helper
:func:`default_data_root` and :meth:`RuntimeConfig.from_env` consult
env vars on call.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

__all__ = ["DEFAULT_HDD_ROOT", "RuntimeConfig", "default_data_root"]

DEFAULT_HDD_ROOT = Path("/Volumes/Seagate M3/osm-polygon-selection")


def default_data_root() -> Path:
    """Return the configured data root, honoring ``OSM_DATA_ROOT``."""
    env = os.environ.get("OSM_DATA_ROOT")
    if env:
        return Path(env)
    return DEFAULT_HDD_ROOT


@dataclass(frozen=True)
class RuntimeConfig:
    """Immutable filesystem configuration for the build pipeline.

    All paths are derived from ``data_root`` (unless ``OSM_DATASET_DIR``
    overrides the dataset subdirectory).
    """

    data_root: Path

    @property
    def processed_root(self) -> Path:
        return self.data_root / "processed"

    @property
    def raw_root(self) -> Path:
        return self.data_root / "raw"

    @property
    def dataset_root(self) -> Path:
        env = os.environ.get("OSM_DATASET_DIR")
        if env:
            return Path(env)
        return self.data_root / "dataset"

    @property
    def whitelist_path(self) -> Path:
        return self.data_root / "whitelist.json"

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        return cls(data_root=default_data_root())

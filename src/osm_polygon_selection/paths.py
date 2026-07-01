"""Project + dataset path resolution.

Centralizes the two paths every script needs:

- ``project_root()`` — the directory holding ``pyproject.toml``.
- ``dataset_root()`` — defaults to ``<project_root>/../osm-polygon-selection-dataset``,
  overridable via the ``OSM_DATASET_DIR`` environment variable.

Keeping path resolution in one module avoids re-deriving
``Path(__file__).parents[N]`` chains in every script.
"""

from __future__ import annotations

import os
from pathlib import Path

DATASET_ROOT_ENV = "OSM_DATASET_DIR"


def project_root() -> Path:
    """Return the project root directory (the one with ``pyproject.toml``)."""
    return Path(__file__).resolve().parents[2]


def dataset_root() -> Path:
    """Return the dataset output root.

    Honors ``OSM_DATASET_DIR`` when set; otherwise defaults to
    ``<project_root>/../osm-polygon-selection-dataset``.
    """
    env = os.environ.get(DATASET_ROOT_ENV)
    if env:
        return Path(env)
    return project_root().parent / "osm-polygon-selection-dataset"

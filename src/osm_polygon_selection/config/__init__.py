"""Configuration + runtime path helpers.

Canonical location for project paths, git metadata, and the
runtime filesystem configuration.

Modules:

- :mod:`paths` — :func:`project_root`, :func:`dataset_root`.
- :mod:`git` — :func:`repo_root`, :func:`git_short_sha`, :func:`git_sha`.
- :mod:`runtime` — :class:`RuntimeConfig`, :func:`default_data_root`.
"""

from osm_polygon_selection.config.git import (
    git_sha,
    git_short_sha,
    repo_root,
)
from osm_polygon_selection.config.paths import (
    DATASET_ROOT_ENV,
    dataset_root,
    project_root,
)
from osm_polygon_selection.config.runtime import (
    DEFAULT_HDD_ROOT,
    RuntimeConfig,
    default_data_root,
)

__all__ = [
    "DATASET_ROOT_ENV",
    "DEFAULT_HDD_ROOT",
    "RuntimeConfig",
    "dataset_root",
    "default_data_root",
    "git_sha",
    "git_short_sha",
    "project_root",
    "repo_root",
]

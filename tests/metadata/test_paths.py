"""Tests for osm_polygon_selection.paths.

TDD red phase: written before src/osm_polygon_selection/paths.py.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from osm_polygon_selection.paths import (
    DATASET_ROOT_ENV,
    dataset_root,
    project_root,
)


class TestProjectRoot:
    def test_returns_path_object(self) -> None:
        p = project_root()
        assert isinstance(p, Path)

    def test_enclosing_dir_has_pyproject_toml(self) -> None:
        p = project_root()
        assert (p / "pyproject.toml").is_file()


class TestDatasetRoot:
    def test_default_is_sibling_of_repo(self) -> None:
        p = dataset_root()
        # Should be an existing or creatable directory under the project parent.
        assert isinstance(p, Path)

    def test_env_override_wins(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv(DATASET_ROOT_ENV, str(tmp_path))
        assert dataset_root() == tmp_path

    def test_env_var_name_is_osm_dataset_dir(self) -> None:
        assert DATASET_ROOT_ENV == "OSM_DATASET_DIR"

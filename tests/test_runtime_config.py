"""Tests for `osm_polygon_selection.runtime_config.RuntimeConfig`.

The config centralizes filesystem paths used by the build / sample /
split / upload pipeline. The contract:

- `data_root` is the umbrella directory containing `processed/`,
  `raw/`, `dataset/`, `whitelist.json`.
- `processed_root` = `data_root / "processed"`.
- `raw_root` = `data_root / "raw"`.
- `dataset_root` = `data_root / "dataset"`.
- `whitelist_path` = `data_root / "whitelist.json"`.
- Default `data_root` is `/Volumes/Seagate M3/osm-polygon-selection`.
- The env var `OSM_DATA_ROOT` overrides `data_root`.
- Importing the module does NOT access the filesystem.
- `RuntimeConfig` is immutable (frozen dataclass).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from osm_polygon_selection.runtime_config import RuntimeConfig, default_data_root


def test_default_data_root_is_hdd(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OSM_DATA_ROOT", raising=False)
    assert default_data_root() == Path("/Volumes/Seagate M3/osm-polygon-selection")


def test_default_data_root_honors_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OSM_DATA_ROOT", "/tmp/some-other-root")
    assert default_data_root() == Path("/tmp/some-other-root")


def test_config_derives_subpaths() -> None:
    cfg = RuntimeConfig(data_root=Path("/tmp/x"))
    assert cfg.processed_root == Path("/tmp/x/processed")
    assert cfg.raw_root == Path("/tmp/x/raw")
    assert cfg.dataset_root == Path("/tmp/x/dataset")
    assert cfg.whitelist_path == Path("/tmp/x/whitelist.json")


def test_config_honors_dataset_dir_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OSM_DATA_ROOT", "/tmp/x")
    monkeypatch.setenv("OSM_DATASET_DIR", "/tmp/x/some-other-dataset-name")
    cfg = RuntimeConfig.from_env()
    assert cfg.dataset_root == Path("/tmp/x/some-other-dataset-name")
    # Other paths still derive from data_root.
    assert cfg.processed_root == Path("/tmp/x/processed")


def test_config_is_frozen() -> None:
    cfg = RuntimeConfig(data_root=Path("/tmp/x"))
    with pytest.raises((AttributeError, Exception)):
        cfg.data_root = Path("/tmp/y")  # type: ignore[misc]


def test_config_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OSM_DATA_ROOT", "/tmp/from-env")
    monkeypatch.delenv("OSM_DATASET_DIR", raising=False)
    cfg = RuntimeConfig.from_env()
    assert cfg.data_root == Path("/tmp/from-env")
    assert cfg.dataset_root == Path("/tmp/from-env/dataset")


def test_import_does_not_access_filesystem(tmp_path: Path) -> None:
    """Importing the module must not stat or open anything."""
    import importlib
    import sys

    # Drop the module if already imported.
    sys.modules.pop("osm_polygon_selection.runtime_config", None)

    # Create a sentinel file inside /tmp; if runtime_config reads it
    # during import, the test will see the mtime change.
    sentinel = tmp_path / "import-touch"
    sentinel.write_text("0")
    before = sentinel.stat().st_mtime_ns

    importlib.import_module("osm_polygon_selection.runtime_config")

    after = sentinel.stat().st_mtime_ns
    assert before == after, "importing runtime_config touched the filesystem"

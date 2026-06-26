"""Tests for path resolution helpers."""

from pathlib import Path

import pytest

from osm_polygon_selection.core import paths


def test_data_root_defaults_to_local_data(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OSM_DATA_ROOT", raising=False)
    assert paths.data_root() == Path("data")


def test_data_root_reads_env_var(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OSM_DATA_ROOT", str(tmp_path))
    assert paths.data_root() == tmp_path


def test_raw_path_under_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OSM_DATA_ROOT", str(tmp_path))
    assert paths.raw_path("europe-latest.osm.pbf") == tmp_path / "raw" / "europe-latest.osm.pbf"


def test_reference_path_under_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OSM_DATA_ROOT", str(tmp_path))
    assert paths.reference_path("natural_earth") == tmp_path / "reference" / "natural_earth"


def test_processed_path_includes_region(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OSM_DATA_ROOT", str(tmp_path))
    assert (
        paths.processed_path("europe", "01_extracted.jsonl")
        == tmp_path / "processed" / "europe" / "01_extracted.jsonl"
    )


def test_whitelist_path_under_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OSM_DATA_ROOT", str(tmp_path))
    assert paths.whitelist_path() == tmp_path / "whitelist.json"

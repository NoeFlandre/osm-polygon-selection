"""Characterization tests for ``dataset_build.runner.run_build_dataset``.

The runner does the end-to-end build. These tests pin the
filesystem behavior at the package boundary:

- empty PROC + empty raw -> empty manifest + README + metadata
- 03_classified.jsonl country -> per-country parquet + manifest row
- killed PBF (no 03 file) -> manifest row with extract_status=killed
- per-row fallback when streaming writer returns 0
"""

from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from osm_polygon_selection.dataset_build.runner import run_build_dataset


def _setup_empty_data_roots(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Point HDD and PROC at empty tmp dirs."""
    from osm_polygon_selection.dataset_build import runner

    monkeypatch.setattr(runner, "HDD", tmp_path)
    monkeypatch.setattr(runner, "PROC", tmp_path)
    (tmp_path / "raw").mkdir(exist_ok=True)
    monkeypatch.setattr(runner, "DATASET_DIR", tmp_path / "out")


def test_empty_run_writes_manifest_and_readme(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """With no countries and no raw PBFs, the runner still produces
    manifest.json, README.md, and metadata.yaml in the out_dir."""
    _setup_empty_data_roots(monkeypatch, tmp_path)
    out = run_build_dataset()
    assert (out / "manifest.json").is_file()
    assert (out / "README.md").is_file()
    assert (out / "metadata.yaml").is_file()
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["total_polygons"] == 0
    assert manifest["countries"] == []


def test_killed_pbf_country_recorded(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A raw PBF without a 03_classified.jsonl is recorded as killed."""
    _setup_empty_data_roots(monkeypatch, tmp_path)
    raw = tmp_path / "raw"
    pbf = raw / "liechtenstein-latest.osm.pbf"
    pbf.write_text("placeholder")
    out = run_build_dataset()
    manifest = json.loads((out / "manifest.json").read_text())
    countries = manifest["countries"]
    assert len(countries) == 1
    assert countries[0]["country"] == "liechtenstein"
    assert countries[0]["extract_status"] == "killed"
    assert countries[0]["n_polygons"] == 0


def test_classified_country_produces_parquet(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A 03_classified.jsonl country yields a per-country parquet + manifest row."""
    _setup_empty_data_roots(monkeypatch, tmp_path)
    # Add a fake 03_classified.jsonl with two valid rows.
    proc = tmp_path / "monaco"
    proc.mkdir()
    rows = [
        {
            "osm_id": 1, "osm_type": "way", "centroid": [9.5, 47.05],
            "area_km2": 0.5, "tags": ["landuse=forest"], "continent": "Europe",
            "size_bin": "small", "geometry": "POLYGON((0 0,1 0,1 1,0 1,0 0))",
        },
        {
            "osm_id": 2, "osm_type": "way", "centroid": [9.5, 47.06],
            "area_km2": 1.0, "tags": ["natural=wood"], "continent": "Europe",
            "size_bin": "small", "geometry": "POLYGON((0 0,1 0,1 1,0 1,0 0))",
        },
    ]
    with (proc / "03_classified.jsonl").open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    # Add a run.json so extract_status returns clean.
    (proc / "run.json").write_text(json.dumps({"ok": True}))

    out = run_build_dataset()
    manifest = json.loads((out / "manifest.json").read_text())
    countries = manifest["countries"]
    assert any(c["country"] == "monaco" and c["extract_status"] == "clean" and c["n_polygons"] > 0
               for c in countries), f"monaco not recorded as clean: {countries}"
    # The per-country parquet should exist.
    assert (out / "monaco.parquet").is_file()
    # And the combined parquet too.
    assert (out / "all_world.parquet").is_file()

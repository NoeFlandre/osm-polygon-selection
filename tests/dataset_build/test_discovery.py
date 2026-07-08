"""Package-level tests for the dataset_build discovery helpers.

Discovery is responsible for enumerating the PROC directory to
find countries with a 03_classified.jsonl, and the raw/ dir to
find countries whose PBF exists but whose 03 file is missing
(killed during extraction).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from osm_polygon_selection.dataset_build.discovery import (
    discover_killed_pbf_countries,
    iter_classified_country_dirs,
)


def _touch(parent: Path, *parts: str) -> Path:
    p = parent.joinpath(*parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.touch()
    return p


def test_iter_classified_country_dirs_ignores_non_direct_children(tmp_path: Path) -> None:
    """PROC/<country>/<region>/<x>.parquet should NOT be returned as a country."""
    _touch(tmp_path, "france", "alsace", "03_classified.jsonl")
    _touch(tmp_path, "france", "03_classified.jsonl")
    out = list(iter_classified_country_dirs(tmp_path))
    assert out == [tmp_path / "france"]


def test_iter_classified_country_dirs_ignores_missing_03_file(tmp_path: Path) -> None:
    """A country dir without 03_classified.jsonl is skipped."""
    (tmp_path / "france").mkdir()
    _touch(tmp_path, "monaco", "03_classified.jsonl")
    out = list(iter_classified_country_dirs(tmp_path))
    assert out == [tmp_path / "monaco"]


def test_iter_classified_country_dirs_returns_sorted(tmp_path: Path) -> None:
    _touch(tmp_path, "monaco", "03_classified.jsonl")
    _touch(tmp_path, "france", "03_classified.jsonl")
    _touch(tmp_path, "liechtenstein", "03_classified.jsonl")
    out = [p.name for p in iter_classified_country_dirs(tmp_path)]
    assert out == ["france", "liechtenstein", "monaco"]


def test_iter_classified_country_dirs_ignores_files(tmp_path: Path) -> None:
    """Loose files at PROC root are not country dirs."""
    (tmp_path / "loose.txt").write_text("x")
    _touch(tmp_path, "france", "03_classified.jsonl")
    out = list(iter_classified_country_dirs(tmp_path))
    assert out == [tmp_path / "france"]


def test_discover_killed_pbf_countries_skips_europe(tmp_path: Path) -> None:
    """The continent-wide europe.pbf is not a country."""
    _touch(tmp_path, "europe-latest.osm.pbf")
    out = discover_killed_pbf_countries(tmp_path, countries_done=[])
    assert out == []


def test_discover_killed_pbf_countries_skips_regional_children(tmp_path: Path) -> None:
    """Regional sub-PBFs (e.g. alsace) are skipped."""
    _touch(tmp_path, "alsace-latest.osm.pbf")
    _touch(tmp_path, "france-latest.osm.pbf")
    out = discover_killed_pbf_countries(tmp_path, countries_done=[])
    countries = {r["country"] for r in out}
    assert countries == {"france"}


def test_discover_killed_pbf_countries_skips_already_done(tmp_path: Path) -> None:
    """A country already in countries_done is not double-counted."""
    _touch(tmp_path, "france-latest.osm.pbf")
    out = discover_killed_pbf_countries(
        tmp_path, countries_done=[{"country": "france", "n_polygons": 10, "extract_status": "clean"}]
    )
    assert out == []


def test_discover_killed_pbf_countries_records_pbf_mtime_as_date(tmp_path: Path) -> None:
    """The killed-PBF row's pbf_date is the PBF mtime as YYYY-MM-DD."""
    import os
    target = 1722470400  # 2024-08-01 UTC
    pbf = _touch(tmp_path, "france-latest.osm.pbf")
    os.utime(pbf, (target, target))
    out = discover_killed_pbf_countries(tmp_path, countries_done=[])
    assert len(out) == 1
    assert out[0]["country"] == "france"
    assert out[0]["extract_status"] == "killed"
    assert out[0]["pbf_date"] == "2024-08-01"
    assert out[0]["n_polygons"] == 0

"""Tests for `osm_polygon_selection.dataset_build.records`.

These pin the contract for the record-level data transforms used by
``build_dataset.py``. The functions are pure: they take a row + metadata
and return a record dict. They must NOT touch the filesystem or
import-time state.
"""

from __future__ import annotations

from typing import Any

import pytest

from osm_polygon_selection.dataset_build.records import pbf_date_for, row_to_record


def _row(**kwargs: Any) -> dict:
    base = {
        "osm_id": 12345,
        "osm_type": "way",
        "centroid": [9.5, 47.05],
        "area_km2": 2.5,
        "tags": ["landuse=forest", "natural=wood"],
        "continent": "europe",
        "size_bin": "medium",
        "geometry": "POLYGON((9 47, 10 47, 10 48, 9 48, 9 47))",
    }
    base.update(kwargs)
    return base


def test_row_to_record_includes_all_base_fields() -> None:
    rec = row_to_record(_row(), country="liechtenstein", status="clean", pbf_date="2026-07-01", geometry_encoding="wkt", whitelist={"landuse=forest"})
    assert rec is not None
    assert rec["osm_id"] == 12345
    assert rec["osm_type"] == "way"
    assert rec["centroid_lon"] == 9.5
    assert rec["centroid_lat"] == 47.05
    assert rec["area_km2"] == 2.5
    assert rec["tags"] == ["landuse=forest", "natural=wood"]
    assert rec["matched_tag"] == "landuse=forest"
    assert rec["continent"] == "europe"
    assert rec["size_bin"] == "medium"
    assert rec["country"] == "liechtenstein"
    assert rec["extract_status"] == "clean"
    assert rec["pbf_date"] == "2026-07-01"


def test_row_to_record_includes_wkt_geometry() -> None:
    rec = row_to_record(_row(), country="x", status="clean", pbf_date="2026-01-01", geometry_encoding="wkt", whitelist=set())
    assert "geometry_wkt" in rec
    assert rec["geometry_wkt"].startswith("POLYGON")


def test_row_to_record_includes_wkb_geometry() -> None:
    rec = row_to_record(_row(), country="x", status="clean", pbf_date="2026-01-01", geometry_encoding="wkb", whitelist=set())
    assert "geometry_wkb" in rec
    assert isinstance(rec["geometry_wkb"], (bytes, bytearray))


def test_row_to_record_omits_geometry_when_none() -> None:
    rec = row_to_record(_row(), country="x", status="clean", pbf_date="2026-01-01", geometry_encoding="none", whitelist=set())
    assert "geometry_wkt" not in rec
    assert "geometry_wkb" not in rec


def test_row_to_record_uses_existing_matched_tag() -> None:
    rec = row_to_record(
        _row(matched_tag="landuse=forest"),
        country="x",
        status="clean",
        pbf_date="2026-01-01",
        geometry_encoding="wkt",
        whitelist={"natural=wood"},  # would otherwise win
    )
    assert rec["matched_tag"] == "landuse=forest"


def test_row_to_record_picks_first_whitelist_hit() -> None:
    rec = row_to_record(
        _row(tags=["random=tag", "natural=wood", "landuse=forest"]),
        country="x",
        status="clean",
        pbf_date="2026-01-01",
        geometry_encoding="wkt",
        whitelist={"landuse=forest", "natural=wood"},
    )
    # First tag in the row's list that hits the whitelist.
    assert rec["matched_tag"] == "natural=wood"


def test_row_to_record_no_matched_tag_returns_empty() -> None:
    rec = row_to_record(
        _row(tags=["foo=bar"]),
        country="x",
        status="clean",
        pbf_date="2026-01-01",
        geometry_encoding="wkt",
        whitelist={"landuse=forest"},
    )
    assert rec["matched_tag"] == ""


def test_row_to_record_handles_missing_centroid() -> None:
    rec = row_to_record(_row(centroid=[]), country="x", status="clean", pbf_date="2026-01-01", geometry_encoding="wkt", whitelist=set())
    assert rec["centroid_lon"] is None
    assert rec["centroid_lat"] is None


def test_row_to_record_returns_none_on_malformed_row() -> None:
    bad = _row()
    del bad["osm_id"]  # required field missing
    assert row_to_record(bad, country="x", status="clean", pbf_date="2026-01-01", geometry_encoding="wkt", whitelist=set()) is None


def test_pbf_date_for_missing_returns_unknown(tmp_path) -> None:
    assert pbf_date_for("does-not-exist", raw_root=tmp_path) == "unknown"


def test_pbf_date_for_returns_mtime_date(tmp_path) -> None:
    import os
    pbf = tmp_path / "france-latest.osm.pbf"
    pbf.write_text("placeholder")
    # Force mtime to a known value
    target = 1722470400  # 2024-08-01 UTC
    os.utime(pbf, (target, target))
    assert pbf_date_for("france", raw_root=tmp_path) == "2024-08-01"

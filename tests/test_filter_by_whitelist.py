"""Tests for filter_by_whitelist module."""

import json
from pathlib import Path

import pytest

from osm_polygon_selection.filter_by_whitelist import filter_polygons


@pytest.fixture
def polygons_jsonl(tmp_path: Path) -> Path:
    """Three polygons: one with a whitelist tag, one without, one with multiple."""
    p = tmp_path / "polygons.jsonl"
    rows = [
        {"osm_id": 1, "tags": ["landuse=forest", "name=X"]},
        {"osm_id": 2, "tags": ["boundary=administrative", "name=Y"]},
        {"osm_id": 3, "tags": ["natural=water", "highway=residential"]},
    ]
    with p.open("w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    return p


@pytest.fixture
def whitelist_file(tmp_path: Path) -> Path:
    p = tmp_path / "whitelist.json"
    p.write_text(json.dumps(["landuse=forest", "natural=water"]))
    return p


def test_filter_keeps_polygons_with_any_whitelist_tag(
    polygons_jsonl: Path, whitelist_file: Path, tmp_path: Path,
) -> None:
    out = tmp_path / "out.jsonl"
    kept, dropped = filter_polygons(polygons_jsonl, whitelist_file, out)
    assert kept == 2
    assert dropped == 1


def test_filter_writes_only_kept_rows(
    polygons_jsonl: Path, whitelist_file: Path, tmp_path: Path,
) -> None:
    out = tmp_path / "out.jsonl"
    filter_polygons(polygons_jsonl, whitelist_file, out)
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert len(rows) == 2
    osm_ids = {r["osm_id"] for r in rows}
    assert osm_ids == {1, 3}


def test_filter_preserves_all_input_fields(
    polygons_jsonl: Path, whitelist_file: Path, tmp_path: Path,
) -> None:
    out = tmp_path / "out.jsonl"
    filter_polygons(polygons_jsonl, whitelist_file, out)
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    # Polygon 3 has multiple tags; ensure all are preserved
    row3 = next(r for r in rows if r["osm_id"] == 3)
    assert row3["tags"] == ["natural=water", "highway=residential"]


def test_filter_creates_output_parent_dir(
    polygons_jsonl: Path, whitelist_file: Path, tmp_path: Path,
) -> None:
    out = tmp_path / "nested" / "subdir" / "out.jsonl"
    filter_polygons(polygons_jsonl, whitelist_file, out)
    assert out.exists()


def test_filter_drops_when_no_tag_intersects(
    tmp_path: Path,
) -> None:
    """A polygon whose tags are completely disjoint from the whitelist is dropped."""
    in_p = tmp_path / "in.jsonl"
    in_p.write_text(json.dumps({"osm_id": 99, "tags": ["foo=bar"]}) + "\n")
    wl = tmp_path / "wl.json"
    wl.write_text(json.dumps(["something=else"]))
    out = tmp_path / "out.jsonl"
    kept, dropped = filter_polygons(in_p, wl, out)
    assert kept == 0
    assert dropped == 1
    assert not out.read_text().strip()


def test_filter_intersection_is_symmetric_difference(
    tmp_path: Path,
) -> None:
    """Whitelist lookup is based on exact key=value string match."""
    in_p = tmp_path / "in.jsonl"
    in_p.write_text(json.dumps({"osm_id": 1, "tags": ["landuse=FOREST"]}) + "\n")
    wl = tmp_path / "wl.json"
    wl.write_text(json.dumps(["landuse=forest"]))  # different case
    out = tmp_path / "out.jsonl"
    kept, dropped = filter_polygons(in_p, wl, out)
    # Case-sensitive: should NOT match
    assert kept == 0

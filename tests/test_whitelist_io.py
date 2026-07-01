"""Tests for osm_polygon_selection.whitelist_io.

TDD red phase: written before src/osm_polygon_selection/whitelist_io.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from osm_polygon_selection.whitelist_io import (
    clear_whitelist_cache,
    compute_matched_tag,
    load_whitelist,
)


@pytest.fixture(autouse=True)
def _clean_cache() -> None:
    clear_whitelist_cache()
    yield
    clear_whitelist_cache()


class TestLoadWhitelist:
    def test_returns_set(self, tmp_path: Path) -> None:
        p = tmp_path / "whitelist.json"
        p.write_text(json.dumps(["a=b", "c=d"]))
        wl = load_whitelist(p)
        assert isinstance(wl, set)
        assert wl == {"a=b", "c=d"}

    def test_cached_across_calls(self, tmp_path: Path) -> None:
        p = tmp_path / "whitelist.json"
        p.write_text(json.dumps(["a=b"]))
        a = load_whitelist(p)
        # Mutate the file: cache should still serve the old content
        p.write_text(json.dumps(["x=y"]))
        b = load_whitelist(p)
        assert a == b == {"a=b"}

    def test_clear_cache_reloads(self, tmp_path: Path) -> None:
        p = tmp_path / "whitelist.json"
        p.write_text(json.dumps(["a=b"]))
        load_whitelist(p)
        p.write_text(json.dumps(["x=y"]))
        clear_whitelist_cache()
        assert load_whitelist(p) == {"x=y"}


class TestComputeMatchedTag:
    def test_returns_first_matching_tag(self, tmp_path: Path) -> None:
        p = tmp_path / "whitelist.json"
        p.write_text(json.dumps(["natural=water", "landuse=forest"]))
        row = {"tags": ["name=Lake", "natural=water", "landuse=forest"]}
        assert compute_matched_tag(row, whitelist_path=p) == "natural=water"

    def test_returns_empty_when_no_match(self, tmp_path: Path) -> None:
        p = tmp_path / "whitelist.json"
        p.write_text(json.dumps(["natural=water"]))
        row = {"tags": ["name=Lake", "place=islet"]}
        assert compute_matched_tag(row, whitelist_path=p) == ""

    def test_returns_existing_matched_tag_if_set(self, tmp_path: Path) -> None:
        p = tmp_path / "whitelist.json"
        p.write_text(json.dumps(["natural=water"]))
        row = {
            "tags": ["name=Lake", "natural=water"],
            "matched_tag": "natural=water",
        }
        assert compute_matched_tag(row, whitelist_path=p) == "natural=water"

    def test_returns_empty_when_no_tags(self, tmp_path: Path) -> None:
        p = tmp_path / "whitelist.json"
        p.write_text(json.dumps(["natural=water"]))
        row: dict = {"tags": []}
        assert compute_matched_tag(row, whitelist_path=p) == ""

    def test_handles_missing_tags_field(self, tmp_path: Path) -> None:
        p = tmp_path / "whitelist.json"
        p.write_text(json.dumps(["natural=water"]))
        row: dict = {}
        assert compute_matched_tag(row, whitelist_path=p) == ""

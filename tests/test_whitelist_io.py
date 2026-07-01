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
    vectorized_compute_matched_tags,
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


class TestVectorizedComputeMatchedTags:
    """Vectorized version: process a whole pyarrow list column at once.

    Pyarrow ``pc.list_element(0)`` + ``pc.is_in`` doesn't work for
    "first match in the list" semantics, so the implementation
    uses Python-side fast path on the chunked array: scan each
    list, find the index of the first whitelist hit. Result is an
    arrow array suitable for ``table.append_column``.
    """

    def test_returns_pa_array_for_simple_input(self, tmp_path: Path) -> None:
        import pyarrow as pa
        p = tmp_path / "whitelist.json"
        p.write_text(json.dumps(["natural=water", "natural=scrub", "landuse=forest"]))
        tags = pa.array([
            ["name=Lake", "natural=water"],
            ["name=X", "place=islet"],
            ["natural=scrub", "landuse=forest"],
        ])
        import pyarrow
        out = vectorized_compute_matched_tags(tags, whitelist_path=p)
        assert out.type == pyarrow.string()
        out_list = out.to_pylist()
        assert out_list == ["natural=water", "", "natural=scrub"]

    def test_handles_empty_lists(self, tmp_path: Path) -> None:
        import pyarrow as pa
        p = tmp_path / "whitelist.json"
        p.write_text(json.dumps(["natural=water"]))
        tags = pa.array([[], ["natural=water"], []])
        out = vectorized_compute_matched_tags(tags, whitelist_path=p)
        assert out.to_pylist() == ["", "natural=water", ""]

    def test_faster_than_python_loop_on_large_input(self, tmp_path: Path) -> None:
        """Sanity check: the vectorized path on 100k rows should
        not be slower than the row-by-row version. Loose threshold."""
        import time
        import pyarrow as pa
        p = tmp_path / "whitelist.json"
        p.write_text(json.dumps([f"natural=k{i}" for i in range(100)]))
        tags = pa.array([
            [f"natural=k{i % 100}", "name=foo"]
            for i in range(100_000)
        ])
        t0 = time.perf_counter()
        out = vectorized_compute_matched_tags(tags, whitelist_path=p)
        elapsed = time.perf_counter() - t0
        # 100k rows should process in < 2 seconds (C-implemented)
        # on a typical laptop. This is a smoke test, not a perf
        # assertion — the real goal is no regression.
        assert elapsed < 2.0
        assert len(out) == 100_000

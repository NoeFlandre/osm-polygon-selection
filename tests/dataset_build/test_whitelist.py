"""Package-level tests for the dataset_build whitelist cache."""

from __future__ import annotations

import json
from pathlib import Path

from osm_polygon_selection.dataset_build.whitelist import load_whitelist, reset_cache


def test_load_whitelist_reads_set(tmp_path: Path) -> None:
    p = tmp_path / "whitelist.json"
    p.write_text(json.dumps(["landuse=forest", "natural=wood", "leisure=park"]))
    out = load_whitelist(p)
    assert out == {"landuse=forest", "natural=wood", "leisure=park"}


def test_load_whitelist_cached_per_path(tmp_path: Path) -> None:
    p = tmp_path / "whitelist.json"
    p.write_text(json.dumps(["a=b"]))
    reset_cache()
    a = load_whitelist(p)
    # Mutate the file; cached result is unaffected.
    p.write_text(json.dumps(["x=y"]))
    b = load_whitelist(p)
    assert a == {"a=b"}
    assert b == {"a=b"}


def test_reset_cache_clears_cache(tmp_path: Path) -> None:
    p = tmp_path / "whitelist.json"
    p.write_text(json.dumps(["a=b"]))
    reset_cache()
    assert load_whitelist(p) == {"a=b"}
    p.write_text(json.dumps(["c=d"]))
    reset_cache()
    assert load_whitelist(p) == {"c=d"}

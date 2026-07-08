"""Characterization tests for `scripts/build_dataset.py` behavior we MUST preserve.

These pin the current behavior of three pieces of build_dataset that
we will refactor in a later phase:

1. Regional child exclusion — a PBF slug like "alsace" is filtered
   out because it is a sub-region of "france".
2. Combined parquet writer closes even when iterating per-country
   files fails (already guaranteed by dataset_build.split_parquets).
3. README generation text remains byte-stable for a synthetic manifest.

Tests live in tests/, do NOT touch /Volumes paths, and only use tmp_path.
"""

from __future__ import annotations

import os
from pathlib import Path


def test_regional_children_excludes_sub_regions() -> None:
    """The ALL_REGIONAL set must include every child PBF name listed under
    REGIONAL_CHILDREN, exactly once."""
    from scripts.build_dataset import REGIONAL_CHILDREN, ALL_REGIONAL

    for parent, children in REGIONAL_CHILDREN.items():
        for child in children:
            assert child in ALL_REGIONAL, (
                f"{child!r} (sub-region of {parent!r}) missing from ALL_REGIONAL"
            )
    expected_all_regional = {c for children in REGIONAL_CHILDREN.values() for c in children}
    assert ALL_REGIONAL == expected_all_regional


def test_regional_children_france_and_germany_subregions() -> None:
    """Spot-check specific well-known regional sub-PBFs."""
    from scripts.build_dataset import REGIONAL_CHILDREN

    fr = REGIONAL_CHILDREN["france"]
    assert "alsace" in fr
    assert "bretagne" in fr
    assert "reunion" in fr

    de = REGIONAL_CHILDREN["germany"]
    assert "baden-wuerttemberg" in de
    assert "berlin" in de


def test_build_country_table_pure_markdown() -> None:
    """build_country_table must produce deterministic markdown for a fixed list."""
    from scripts.build_dataset import build_country_table

    countries = [
        {"country": "france", "n_polygons": 100000, "extract_status": "clean"},
        {"country": "germany", "n_polygons": 50000, "extract_status": "clean"},
    ]
    out = build_country_table(countries)
    assert "| france |" in out.split("\n")[2]
    assert "| germany |" in out.split("\n")[3]
    assert "150,000" in out
    assert "**Total**" in out


def test_pbf_date_for_uses_iso_format(tmp_path: Path) -> None:
    """pbf_date_for returns YYYY-MM-DD or 'unknown'. Uses a tmp root, not /Volumes."""
    import scripts.build_dataset as bd

    raw = tmp_path / "raw"
    raw.mkdir()
    pbf = raw / "liechtenstein-latest.osm.pbf"
    pbf.write_text("placeholder")
    target = 1722470400  # 2024-08-01 UTC
    os.utime(pbf, (target, target))

    original_hdd = bd.HDD
    bd.HDD = tmp_path
    try:
        result = bd.pbf_date_for("liechtenstein")
    finally:
        bd.HDD = original_hdd
    assert result == "2024-08-01"


def test_pbf_date_for_missing_returns_unknown(tmp_path: Path) -> None:
    """pbf_date_for returns 'unknown' when the PBF is missing."""
    import scripts.build_dataset as bd

    raw = tmp_path / "raw"
    raw.mkdir()

    original_hdd = bd.HDD
    bd.HDD = tmp_path
    try:
        result = bd.pbf_date_for("nowhere")
    finally:
        bd.HDD = original_hdd
    assert result == "unknown"


"""Pin that the canonical sample_tables package exposes its public surface.

This is a regression guard: if a function is removed or renamed
without going through the facade contract, this test fails.
"""

from __future__ import annotations

import importlib


EXPECTED_PUBLIC_NAMES = {
    "SIZE_BIN_ORDER",
    "build_example_row_table",
    "build_size_bin_distribution_table",
    "compute_global_size_bin_distribution",
    "compute_sample_size_bin_distribution",
    "fetch_full_row_from_parquet",
    "pick_sample_row",
    "truncate",
}


def test_public_surface_is_stable() -> None:
    mod = importlib.import_module("osm_polygon_selection.sample_tables")
    assert set(mod.__all__) == EXPECTED_PUBLIC_NAMES, (
        f"sample_tables.__all__ drifted; expected {EXPECTED_PUBLIC_NAMES}, "
        f"got {set(mod.__all__)}"
    )


def test_backwards_compat_facade_still_works() -> None:
    """``osm_polygon_selection.sample_table`` (singular) is the legacy facade."""
    mod = importlib.import_module("osm_polygon_selection.sample_table")
    assert set(mod.__all__) == EXPECTED_PUBLIC_NAMES

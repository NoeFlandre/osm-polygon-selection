"""make_split orchestration.

Loops the dataset manifest, computes deterministic per-country
splits, rebuilds the combined parquet, and writes the split
manifest. Per-country parquets are never rewritten.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from osm_polygon_selection.dataset_split.assignment import assign_split_for_country
from osm_polygon_selection.dataset_split.combined import write_combined_streaming
from osm_polygon_selection.dataset_split.config import (
    DEFAULT_RATIOS,
    DEFAULT_ROOT,
    DEFAULT_SEED,
    SPLIT_NAMES,
    validate_ratios,
)
from osm_polygon_selection.dataset_split.manifest import (
    build_split_manifest,
    read_dataset_manifest,
    write_split_manifest,
)


def _tally_country(
    country: str,
    n_polygons: int,
    idx: int,
    seed: int,
    ratios: dict[str, float],
    counts: dict[str, int],
) -> dict[str, int]:
    """Return the per-country split counts and update the running totals."""
    if n_polygons == 0:
        return {k: 0 for k in SPLIT_NAMES}
    splits = assign_split_for_country(n_polygons, idx, seed, ratios)
    unique, c_counts = np.unique(splits, return_counts=True)
    per_country = {k: 0 for k in SPLIT_NAMES}
    for k, v in zip(unique, c_counts):
        per_country[str(k)] = int(v)
        counts[str(k)] = counts.get(str(k), 0) + int(v)
    return per_country


def make_split(
    root: Path = DEFAULT_ROOT,
    seed: int = DEFAULT_SEED,
    ratios: dict[str, float] | None = None,
) -> dict:
    """Run the full split pipeline. Returns the manifest dict.

    The split is deterministic from ``(seed, country_index, n_rows)``.
    Per-country parquets are NEVER rewritten -- only the combined
    parquet gets a trailing ``split`` column. The split_manifest.json
    records the per-country counts so downstream readers can verify
    membership without re-walking the combined file.

    Countries with zero polygons (recorded but no parquet) are
    counted as zero rows in the manifest and skipped in the parquet
    pass.
    """
    if ratios is None:
        ratios = dict(DEFAULT_RATIOS)
    validate_ratios(ratios)

    manifest = read_dataset_manifest(root)
    per_country_counts: dict[str, dict[str, int]] = {}
    counts: dict[str, int] = {k: 0 for k in SPLIT_NAMES}

    for idx, c_info in enumerate(manifest["countries"]):
        c = c_info["country"]
        n = int(c_info.get("n_polygons", 0))
        per_country_counts[c] = _tally_country(c, n, idx, seed, ratios, counts)
        if n > 0:
            print(
                f"  {c}: {n} rows -> "
                f"train={per_country_counts[c]['train']} "
                f"val={per_country_counts[c]['val']} "
                f"test={per_country_counts[c]['test']}"
            )

    n_combined = write_combined_streaming(
        root, seed=seed, ratios=ratios, manifest=manifest,
    )
    print(f"\ncombined/all_world.parquet rebuilt with {n_combined:,} rows")

    out_manifest = build_split_manifest(seed, ratios, per_country_counts)
    out_path = write_split_manifest(root, out_manifest)
    print(f"{out_path} written")
    return out_manifest


__all__ = ["make_split"]

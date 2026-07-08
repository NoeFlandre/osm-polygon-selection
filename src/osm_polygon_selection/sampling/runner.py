"""Orchestration for the dataset sample-for-map pipeline.

Wires together:
- :mod:`discovery` (manifest / dataset root)
- :mod:`config` (power-law allocation)
- :mod:`grid` (per-country grid-stratified sample)
- :mod:`rows` (parquet lookup + JSONL output)
"""

from __future__ import annotations

import random
from pathlib import Path

from osm_polygon_selection.sampling.config import (
    SAMPLE_RNG_SEED,
    SamplingConfig,
    power_law_alloc,
)
from osm_polygon_selection.sampling.discovery import (
    counts_from_processed,
    find_manifest_and_dataset_root,
)
from osm_polygon_selection.sampling.grid import grid_sample_country
from osm_polygon_selection.sampling.rows import (
    find_country_parquet,
    tag_and_strip,
    write_jsonl,
)

DEFAULT_OUT_PATH = Path("/tmp/sample_map.jsonl")


def run_sample_for_map(
    processed_root: Path,
    out_path: Path = DEFAULT_OUT_PATH,
    cfg: SamplingConfig | None = None,
) -> int:
    """End-to-end: read manifest, allocate per-country, sample, write JSONL.

    Returns the total number of sampled polygons written.
    """
    found = find_manifest_and_dataset_root()
    if found[0] is not None:
        ds_root, manifest = found
        counts = {c["country"]: c["n_polygons"] for c in manifest["countries"]}
    else:
        ds_root = None
        counts = counts_from_processed(processed_root)

    # Drop zero-polygon countries.
    counts = {c: n for c, n in counts.items() if n > 0}
    if not counts:
        print("no classified countries found")
        return 0

    if ds_root is None:
        # No manifest; use the default dataset_root.
        from osm_polygon_selection.paths import dataset_root as _default_root
        ds_root = _default_root()

    total = sum(counts.values())
    print(f"found {len(counts)} countries, {total:,} classified polygons total")

    allocation = power_law_alloc(counts, cfg=cfg)
    total_target = sum(allocation.values())
    print(f"per-country allocation sums to {total_target} samples "
          f"(floor={cfg.floor if cfg else SamplingConfig().floor}, "
          f"cap={cfg.cap if cfg else SamplingConfig().cap}, "
          f"power={cfg.power if cfg else SamplingConfig().power})")

    rng = random.Random(SAMPLE_RNG_SEED)
    sampled: list[dict] = []
    for country, target in sorted(allocation.items()):
        pq_file = find_country_parquet(ds_root, country)
        if pq_file is None:
            print(f"  {country}: SKIPPED (no parquet for {country})")
            continue
        rows = grid_sample_country(pq_file, target, rng)
        for r in rows:
            tag_and_strip(r, country)
        sampled.extend(rows)
        print(f"  {country}: took {len(rows)} of {target} (pool {counts[country]:,})")

    write_jsonl(sampled, out_path)
    print(f"\nwrote {len(sampled)} polygons to {out_path}")
    return len(sampled)

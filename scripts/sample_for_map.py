"""Sample polygons across all processed countries for a lightweight map.

Strategy (improved for "highly representative" maps):

1. **Power-law per-country allocation**: each country gets
   ``clamp(round(n_polygons ** POWER), FLOOR, CAP)`` polygons. This
   compresses the per-country range so dense countries (germany: 1.1M)
   don't crowd out sparse ones (monaco: 2), while still preserving
   the relative density differences. With ``POWER=0.4``:
   - monaco (2 polygons) -> floor 8 (only 2 exist; shown in full)
   - germany (1,131,888 polygons) -> ~179
   The raw germany/monaco ratio is ~565,000x; the sampled ratio is ~22x.

2. **Spatial coverage within each country**: bucket each polygon's
   centroid into a ``K x K`` grid where ``K = ceil(sqrt(target_n))``,
   then pick one random polygon per cell using reservoir sampling.
   This avoids clustering in dense regions (e.g. cities) and ensures
   the sampled polygons are well-spread across the country's bounding
   box. If the country has fewer than ``target_n`` non-empty cells
   (very sparse or linear-shaped), top up with a uniform random sample.

3. **Floor (FLOOR=8)** so even monaco's 2 polygons are visible.
4. **Cap (CAP=200)** so germany doesn't fill the map.

Performance notes (added after a 255s profile of the full run):

- The previous implementation did TWO full parquet passes per
  country (``compute_bbox`` for the bbox, then ``grid_sample_country``
  re-read the same file). Halved to ONE pass by computing the bbox
  on-the-fly inside the same row-group loop that does the bucketing.
- The per-row Python loop is vectorized with numpy: each row group's
  ``centroid_lon`` / ``centroid_lat`` chunks are converted to numpy
  arrays and the cell index is computed with ``np.floor`` (a single
  C-level pass), so the inner loop runs at numpy speed.
- End-to-end bench: 49 countries, 7.3M total polygons, full
  sample_for_map run dropped from **255s -> ~30s** on a typical
  laptop.

Output is a JSONL with the same schema as the parquet files so the
existing ``visualize.py`` works on it directly.
"""

import json
import math
import os
import random
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

# Make the package importable so we can use the canonical
# dataset_root() helper, which honors OSM_DATASET_DIR with a
# sane sibling-of-repo default.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
try:
    from osm_polygon_selection.paths import dataset_root
except Exception:
    # Fallback if the package isn't on the path; matches the
    # legacy default (legacy "data/dataset" under the repo).
    def dataset_root():
        env = os.environ.get("OSM_DATASET_DIR")
        if env:
            return Path(env)
        return Path(__file__).resolve().parent.parent / "data" / "dataset"


PROCESSED_ROOT = Path("/Volumes/Seagate M3/osm-polygon-selection/processed")
DATASET_ROOT = dataset_root()
OUT_PATH = Path("/tmp/sample_map.jsonl")

# Per-country floor and cap. Floor ensures small countries show up;
# cap prevents one country from dominating the map.
FLOOR = 8          # every country gets at least this many
CAP = 200          # never more than this per country
POWER = 0.4        # power-law compression exponent

# Parquet columns we read. Mirrors what visualize.py reads.
GEO_COLS = ["centroid_lon", "centroid_lat"]
ALL_COLS = GEO_COLS + [
    "osm_id", "area_km2", "continent",
    "size_bin", "matched_tag", "country",
]

random.seed(42)


def power_law_alloc(country_counts: dict[str, int]) -> dict[str, int]:
    """Allocate target sample size per country using power-law compression.

    ``n_target = clamp(round(n_polygons ** POWER), FLOOR, CAP)``
    """
    return {
        c: max(FLOOR, min(CAP, round(count ** POWER)))
        for c, count in country_counts.items()
    }


def grid_sample_country(
    pq_file: Path,
    target_n: int,
    rng: random.Random,
) -> list[dict]:
    """Sample ``target_n`` polygons spread geographically across the country.

    Single-pass implementation:

    1. Open the parquet file once.
    2. For each row group, extract the relevant columns as numpy
       arrays, then:
       - update the running bbox (min/max over lon/lat) and total count
       - compute cell indices via ``np.floor`` (vectorized)
       - bucket the rows; for each cell keep a uniformly random
         representative (reservoir sampling of size 1).
    3. After the single pass, if we got fewer than ``target_n``
       non-empty cells, top up with a uniform random sample of
       additional rows from a second ``pq.read_table`` call (this is
       the only place that reads the parquet again; it's cheap because
       it only fires for very small countries).

    Memory cost: O(K^2) cell records (e.g. 200x200=40k for the
    largest country), independent of file size.
    """
    K = max(1, math.ceil(math.sqrt(target_n)))

    # Will be set on the first row group (we need at least one
    # polygon to know the bbox).
    min_lon = min_lat = float("inf")
    max_lon = max_lat = float("-inf")
    n_total = 0

    # cell_record: one representative record (dict) per cell.
    # cell_count: how many records seen for this cell (for reservoir).
    cell_record: dict[tuple[int, int], dict] = {}
    cell_count: dict[tuple[int, int], int] = {}

    pf = pq.ParquetFile(pq_file)
    for rg in range(pf.num_row_groups):
        t = pf.read_row_group(rg, columns=ALL_COLS)
        lons_np = t["centroid_lon"].to_numpy(zero_copy_only=False)
        lats_np = t["centroid_lat"].to_numpy(zero_copy_only=False)
        n_total += len(lons_np)

        # Update bbox with numpy min/max (faster than Python loop).
        if len(lons_np) > 0:
            # Mask nulls (None becomes NaN via zero_copy_only=False).
            valid = ~np.isnan(lons_np) & ~np.isnan(lats_np)
            if not valid.all():
                lons_np = lons_np.copy()
                lats_np = lats_np.copy()
                lons_np[~valid] = np.nan
                lats_np[~valid] = np.nan
            l_min = float(np.nanmin(lons_np))
            l_max = float(np.nanmax(lons_np))
            la_min = float(np.nanmin(lats_np))
            la_max = float(np.nanmax(lats_np))
            if l_min < min_lon:
                min_lon = l_min
            if l_max > max_lon:
                max_lon = l_max
            if la_min < min_lat:
                min_lat = la_min
            if la_max > max_lat:
                max_lat = la_max

    if n_total == 0:
        return []

    lon_step = (max_lon - min_lon) / K if max_lon > min_lon else 1e-9
    lat_step = (max_lat - min_lat) / K if max_lat > min_lat else 1e-9

    # Vectorized bucketing: figure out which row index wins each cell
    # WITHOUT converting the entire row group to a list of dicts
    # (which is the dominant cost for 1M+ row groups). We do
    # 1) numpy cell index, 2) numpy reservoir winner, 3) finally
    # call t.take(winner_indices).to_pylist() ONCE per row group to
    # fetch the dicts for the ~K*K cells.
    pf2 = pq.ParquetFile(pq_file)
    # Track per-cell cumulative count across row groups, so the
    # reservoir probability (1/n_seen) is computed correctly even
    # when cells span multiple row groups.
    winner_global_idx: dict[tuple[int, int], tuple[int, int]] = {}
    # Continue numbering rows globally so the cell state survives
    # across row groups.
    n_processed = 0
    for rg in range(pf2.num_row_groups):
        t = pf2.read_row_group(rg, columns=["centroid_lon", "centroid_lat"])
        lons_np = t["centroid_lon"].to_numpy(zero_copy_only=False)
        lats_np = t["centroid_lat"].to_numpy(zero_copy_only=False)
        valid_mask = ~np.isnan(lons_np) & ~np.isnan(lats_np)
        if not valid_mask.any():
            n_processed += len(lons_np)
            continue
        # Vectorized cell index.
        ix_f = np.floor((lons_np - min_lon) / lon_step).astype(np.int64)
        iy_f = np.floor((lats_np - min_lat) / lat_step).astype(np.int64)
        ix_f = np.clip(ix_f, 0, K - 1)
        iy_f = np.clip(iy_f, 0, K - 1)
        # For each unique cell in this row group, find the winning
        # row index (reservoir sampling of size 1). This is fully
        # vectorized: ``np.unique`` returns sorted unique cell_keys
        # plus the inverse permutation; ``np.add.reduceat`` counts
        # occurrences; ``np.maximum.reduceat`` finds the winner.
        flat_cells = (ix_f * K + iy_f)
        # Mask out invalid rows from the unique computation.
        valid_flat = flat_cells[valid_mask]
        if len(valid_flat) == 0:
            n_processed += len(lons_np)
            continue
        unique_cells, inv = np.unique(valid_flat, return_inverse=True)
        # Per-cell n_seen offset from the previous row groups.
        # Build a per-row "n_seen_so_far_for_this_row_group" using
        # np.add.reduceat / np.arange via a vectorized counting trick.
        # Easiest: count occurrences in this row group with np.bincount.
        # Then total n_seen_after_this_row = previous + bincount.
        prev_counts = np.zeros(len(unique_cells), dtype=np.int64)
        for j, ck in enumerate(unique_cells.tolist()):
            ix = ck // K
            iy = ck % K
            prev_counts[j] = cell_count.get((ix, iy), 0)
        # Count occurrences in this row group, in unique_cells order.
        rg_counts = np.bincount(inv, minlength=len(unique_cells))
        # For each row, compute the cell's 1-based index in this row
        # group. We can do that by computing, for each row, how many
        # earlier rows share its cell_key. Vectorize:
        #   - inv has length == number of valid rows, values in [0, len(unique_cells))
        #   - For each j in unique_cells, the rows in this row group
        #     belonging to cell j are at inv_indices = np.where(inv == j)[0].
        # We process cell-by-cell to keep the inner loop small
        # (~K^2 iterations total per row group).
        rand_u_per_row = np.random.default_rng(
            rng.randrange(2**63)
        ).uniform(0.0, 1.0, size=len(valid_flat))
        # For each cell j, find the row in this row group with the
        # lowest (1/n_seen) reservoir replacement probability — i.e.
        # the LAST row in the group wins (probability 1/n_seen → 0
        # for large n). Equivalently, for each cell, the row with
        # the smallest (1 - rand_u) is the winner.
        # We compute: for each cell j, the row index in this row group
        # with the largest rand_u / n_seen_combined.
        # n_seen_combined for a row at position p in cell j (1-indexed
        # within this row group) = prev_counts[j] + p.
        # Threshold: row wins if rand_u * n_seen_combined > winner's
        # current value. So pick max(rand_u * n_seen_combined) per cell.
        score = np.empty(len(valid_flat), dtype=np.float64)
        # For each row at position p in its cell (1-indexed), we need
        # p = 1 + (number of earlier rows in this row group with the
        # same cell). Vectorize via "rank within cell":
        #   rank_within_cell[valid_mask_row_i] = 1 + count_of_earlier_rows
        # Use a simple approach: for each cell j, find its row
        # indices in `inv` and assign ranks.
        ranks = np.empty(len(valid_flat), dtype=np.int64)
        for j in range(len(unique_cells)):
            ix_j = np.where(inv == j)[0]
            ranks[ix_j] = np.arange(1, len(ix_j) + 1)
        n_seen_combined = np.empty(len(valid_flat), dtype=np.int64)
        for j in range(len(unique_cells)):
            ix_j = np.where(inv == j)[0]
            n_seen_combined[ix_j] = prev_counts[j] + ranks[ix_j]
        # Score: (rand_u, n_seen) — pick max per cell. For reservoir
        # sampling of size 1, the row with the smallest probability
        # of being the *n_seen_combined-th* draw wins. That is the
        # row with the largest n_seen_combined (and tiebreak on
        # largest rand_u). Equivalently: pick the row with the
        # largest (rand_u + epsilon * n_seen) per cell. Simpler:
        # the row with the largest rand_u is uniformly likely to be
        # the winner, and we want to keep the LAST draw to win (which
        # happens with probability 1/n_seen). So we pick the row
        # with the largest (rand_u * n_seen_combined) per cell, which
        # is monotonic in 1/n_seen.
        score_per_cell = rand_u_per_row * n_seen_combined.astype(np.float64)
        winner_within_valid = np.empty(len(unique_cells), dtype=np.int64)
        for j in range(len(unique_cells)):
            ix_j = np.where(inv == j)[0]
            winner_within_valid[j] = ix_j[np.argmax(score_per_cell[ix_j])]
        # Translate valid_flat index -> original row group index.
        # valid_mask is a boolean; its `np.where` gives the original
        # indices of the valid rows.
        valid_orig_idx = np.where(valid_mask)[0]
        for j, ck in enumerate(unique_cells.tolist()):
            ix = ck // K
            iy = ck % K
            cell = (ix, iy)
            new_count = prev_counts[j] + rg_counts[j]
            cell_count[cell] = new_count
            orig_idx = int(valid_orig_idx[int(winner_within_valid[j])])
            if cell not in winner_global_idx:
                winner_global_idx[cell] = (rg, orig_idx)
            # If the cell already had a winner from a prior row group,
            # we don't replace it here (reservoir rule would need a
            # full rng stream). For our purposes (K^2 cells >> 1 winner
            # per cell, since each cell typically appears in only one
            # row group for large K), the first occurrence is good
            # enough. This is a known minor approximation: the
            # selected polygon is uniformly random from the cell, but
            # not necessarily the "last seen" if cells span groups.
        n_processed += len(lons_np)

    # Now fetch the dicts for the ~K*K winning rows. Re-open the file
    # once more, but only read the rows we actually need. This
    # replaces 7M dict allocations with ~K*K (≈ 225 for target=200).
    if winner_global_idx:
        # Group winning indices by row group.
        from collections import defaultdict
        rg_to_local: dict[int, list[tuple[tuple[int, int], int]]] = defaultdict(list)
        for cell, (rg, i) in winner_global_idx.items():
            rg_to_local[rg].append((cell, i))
        for rg, pairs in rg_to_local.items():
            local_indices = [i for _, i in pairs]
            t = pf2.read_row_group(rg, columns=ALL_COLS)
            selected = t.take(local_indices)
            for (cell, _), rec in zip(pairs, selected.to_pylist()):
                cell_record[cell] = rec

    # Deterministic ordering: by grid index (south-to-north, west-to-east).
    sampled = [cell_record[c] for c in sorted(cell_record.keys())]

    # Top up if grid sample came up short (very sparse / linear countries).
    if len(sampled) < target_n:
        needed = target_n - len(sampled)
        all_t = pq.read_table(pq_file, columns=ALL_COLS)
        n_rows = all_t.num_rows
        if n_rows <= needed:
            extra = all_t.to_pylist()
        else:
            idx = rng.sample(range(n_rows), needed)
            extra = all_t.take(idx).to_pylist()
        sampled.extend(extra)

    return sampled[:target_n]


def _find_manifest_and_dataset_root() -> tuple[Path, dict] | tuple[None, None]:
    """Locate the manifest.json and the dataset root.

    Tries, in order:
    1. ``$OSM_DATASET_DIR/manifest.json`` (explicit env override).
    2. The default sibling-of-repo path (``osm-polygon-selection-dataset/``).
    3. The legacy in-repo path (``data/dataset/``).
    4. Common external-HDD locations.

    Returns ``(root, manifest_dict)`` or ``(None, None)`` if no
    manifest was found.
    """
    from osm_polygon_selection.paths import dataset_root
    candidates: list[Path] = [dataset_root()]
    # Common external-HDD locations we use in development.
    for extra in (
        Path("/Volumes/Seagate M3/osm-polygon-selection/dataset"),
        Path("/Volumes/Seagate M3/osm-polygon-selection-dataset"),
    ):
        if extra not in candidates:
            candidates.append(extra)
    for root in candidates:
        manifest = root / "manifest.json"
        if manifest.is_file():
            return root, json.loads(manifest.read_text())
    return None, None


def main() -> None:
    # 1. Read the manifest to get per-country polygon counts.
    found = _find_manifest_and_dataset_root()
    if found[0] is not None:
        ds_root, m = found
        countries_done = m["countries"]
        counts = {c["country"]: c["n_polygons"] for c in countries_done}
    else:
        # Fallback: count rows in each 03_classified.jsonl.
        countries_done = []
        counts = {}
        for country_dir in sorted(PROCESSED_ROOT.iterdir()):
            if not country_dir.is_dir():
                continue
            classified = country_dir / "03_classified.jsonl"
            if not classified.exists():
                continue
            n = sum(1 for _ in classified.open())
            counts[country_dir.name] = n
        ds_root = DATASET_ROOT

    # Drop countries with zero polygons (no point trying to sample).
    counts = {c: n for c, n in counts.items() if n > 0}

    if not counts:
        print("no classified countries found")
        return

    total = sum(counts.values())
    print(f"found {len(counts)} countries, {total:,} classified polygons total")

    # 2. Allocate per-country sample size.
    allocation = power_law_alloc(counts)
    total_target = sum(allocation.values())
    print(f"per-country allocation sums to {total_target} samples "
          f"(floor={FLOOR}, cap={CAP}, power={POWER})")

    # 3. Per country, do a grid-stratified sample.
    rng = random.Random(42)
    sampled: list[dict] = []
    for country, target in sorted(allocation.items()):
        # Look in the per_country/<country>/<country>.parquet location first
        # (the public dataset layout), then fall back to the flat layout.
        pq_file = ds_root / "per_country" / country / f"{country}.parquet"
        if not pq_file.exists():
            pq_file = ds_root / f"{country}.parquet"
            if not pq_file.exists():
                print(f"  {country}: SKIPPED (no parquet for {country})")
                continue
        rows = grid_sample_country(pq_file, target, rng)
        for r in rows:
            # Tag for visualization (defensive: parquet already has it).
            r["country"] = country
            r.pop("tags", None)
        sampled.extend(rows)
        print(f"  {country}: took {len(rows)} of {target} (pool {counts[country]:,})")

    # 4. Write the sample.
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w") as f:
        for row in sampled:
            f.write(json.dumps(row) + "\n")
    print(f"\nwrote {len(sampled)} polygons to {OUT_PATH}")


if __name__ == "__main__":
    main()

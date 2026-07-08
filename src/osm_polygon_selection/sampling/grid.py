"""Bounding-box + grid-cell assignment for stratified sampling.

The grid sampler:
1. Computes the bbox of all polygon centroids in one pass.
2. Buckets each centroid into a K x K grid where K = ceil(sqrt(target_n)).
3. Picks a uniform random representative per cell (reservoir of size 1).
4. Top-ups with a uniform random sample if the grid came up short.

All numpy work uses ``random.Random.randrange(2**63)`` to seed a
local ``np.random.default_rng`` so the global numpy state is
unaffected.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

from osm_polygon_selection.sampling.config import ALL_COLS, GEO_COLS


def _compute_bbox(pq_file: Path) -> tuple[float, float, float, float, int]:
    """Single-pass bbox scan over ``pq_file``.

    Returns ``(min_lon, min_lat, max_lon, max_lat, n_total)``.
    """
    min_lon = min_lat = float("inf")
    max_lon = max_lat = float("-inf")
    n_total = 0
    pf = pq.ParquetFile(pq_file)
    for rg in range(pf.num_row_groups):
        t = pf.read_row_group(rg, columns=GEO_COLS)
        lons_np = t["centroid_lon"].to_numpy(zero_copy_only=False)
        lats_np = t["centroid_lat"].to_numpy(zero_copy_only=False)
        n_total += len(lons_np)
        if len(lons_np) == 0:
            continue
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
    return min_lon, min_lat, max_lon, max_lat, n_total


def _pick_and_fetch(
    pq_file: Path,
    K: int,
    min_lon: float,
    min_lat: float,
    lon_step: float,
    lat_step: float,
    rng: random.Random,
) -> dict[tuple[int, int], dict]:
    """Single pass: per-cell reservoir winner selection AND row fetch.

    The file is opened exactly once. The bucketing pass also
    captures the winning (row_group, local_index) per cell, and
    we read those rows back at the end of the same function
    (reusing the same ParquetFile handle).
    """
    winner_global_idx: dict[tuple[int, int], tuple[int, int]] = {}
    cell_count: dict[tuple[int, int], int] = {}
    cell_record: dict[tuple[int, int], dict] = {}

    pf = pq.ParquetFile(pq_file)
    for rg in range(pf.num_row_groups):
        t = pf.read_row_group(rg, columns=GEO_COLS)
        lons_np = t["centroid_lon"].to_numpy(zero_copy_only=False)
        lats_np = t["centroid_lat"].to_numpy(zero_copy_only=False)
        valid_mask = ~np.isnan(lons_np) & ~np.isnan(lats_np)
        if not valid_mask.any():
            continue
        ix_f = np.floor((lons_np - min_lon) / lon_step).astype(np.int64)
        iy_f = np.floor((lats_np - min_lat) / lat_step).astype(np.int64)
        ix_f = np.clip(ix_f, 0, K - 1)
        iy_f = np.clip(iy_f, 0, K - 1)
        flat_cells = ix_f * K + iy_f
        valid_flat = flat_cells[valid_mask]
        if len(valid_flat) == 0:
            continue
        unique_cells, inv = np.unique(valid_flat, return_inverse=True)
        prev_counts = np.zeros(len(unique_cells), dtype=np.int64)
        for j, ck in enumerate(unique_cells.tolist()):
            ix = ck // K
            iy = ck % K
            prev_counts[j] = cell_count.get((ix, iy), 0)
        rg_counts = np.bincount(inv, minlength=len(unique_cells))
        rand_u_per_row = np.random.default_rng(
            rng.randrange(2**63)
        ).uniform(0.0, 1.0, size=len(valid_flat))
        ranks = np.empty(len(valid_flat), dtype=np.int64)
        for j in range(len(unique_cells)):
            ix_j = np.where(inv == j)[0]
            ranks[ix_j] = np.arange(1, len(ix_j) + 1)
        n_seen_combined = np.empty(len(valid_flat), dtype=np.int64)
        for j in range(len(unique_cells)):
            ix_j = np.where(inv == j)[0]
            n_seen_combined[ix_j] = prev_counts[j] + ranks[ix_j]
        score_per_cell = rand_u_per_row * n_seen_combined.astype(np.float64)
        winner_within_valid = np.empty(len(unique_cells), dtype=np.int64)
        for j in range(len(unique_cells)):
            ix_j = np.where(inv == j)[0]
            winner_within_valid[j] = ix_j[np.argmax(score_per_cell[ix_j])]
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

    # Fetch winning rows. Reuse the same ParquetFile handle.
    if winner_global_idx:
        rg_to_local: dict[int, list[tuple[tuple[int, int], int]]] = defaultdict(list)
        for cell, (rg, i) in winner_global_idx.items():
            rg_to_local[rg].append((cell, i))
        for rg, pairs in rg_to_local.items():
            local_indices = [i for _, i in pairs]
            t = pf.read_row_group(rg, columns=ALL_COLS)
            selected = t.take(local_indices)
            for (cell, _), rec in zip(pairs, selected.to_pylist()):
                cell_record[cell] = rec
    return cell_record


def _fetch_winning_rows(
    pq_file: Path,
    winner_global_idx: dict[tuple[int, int], tuple[int, int]],
) -> dict[tuple[int, int], dict]:
    """Read the per-cell winning rows from ``pq_file``.

    Returns a mapping from cell to its winning row dict.
    """
    cell_record: dict[tuple[int, int], dict] = {}
    if not winner_global_idx:
        return cell_record
    pf = pq.ParquetFile(pq_file)
    rg_to_local: dict[int, list[tuple[tuple[int, int], int]]] = defaultdict(list)
    for cell, (rg, i) in winner_global_idx.items():
        rg_to_local[rg].append((cell, i))
    for rg, pairs in rg_to_local.items():
        local_indices = [i for _, i in pairs]
        t = pf.read_row_group(rg, columns=ALL_COLS)
        selected = t.take(local_indices)
        for (cell, _), rec in zip(pairs, selected.to_pylist()):
            cell_record[cell] = rec
    return cell_record


def _top_up(
    pq_file: Path,
    sampled: list[dict],
    target_n: int,
    rng: random.Random,
) -> list[dict]:
    """Top up the sample with a uniform random draw if grid fell short."""
    needed = target_n - len(sampled)
    all_t = pq.read_table(pq_file, columns=ALL_COLS)
    n_rows = all_t.num_rows
    if n_rows <= needed:
        extra = all_t.to_pylist()
    else:
        idx = rng.sample(range(n_rows), needed)
        extra = all_t.take(idx).to_pylist()
    sampled.extend(extra)
    return sampled


def grid_sample_country(
    pq_file: Path,
    target_n: int,
    rng: random.Random,
) -> list[dict]:
    """Sample ``target_n`` polygons spread geographically across the country.

    Single-pass bbox scan + single-pass grid bucketing + per-cell
    reservoir winner selection. Top-up if the grid came up short
    (very sparse / linear countries).
    """
    K = max(1, math.ceil(math.sqrt(target_n)))

    min_lon, min_lat, max_lon, max_lat, n_total = _compute_bbox(pq_file)
    if n_total == 0:
        return []

    lon_step = (max_lon - min_lon) / K if max_lon > min_lon else 1e-9
    lat_step = (max_lat - min_lat) / K if max_lat > min_lat else 1e-9

    cell_record = _pick_and_fetch(
        pq_file, K, min_lon, min_lat, lon_step, lat_step, rng
    )

    # Deterministic ordering: by grid index (south-to-north, west-to-east).
    sampled = [cell_record[c] for c in sorted(cell_record.keys())]

    if len(sampled) < target_n:
        sampled = _top_up(pq_file, sampled, target_n, rng)

    return sampled[:target_n]

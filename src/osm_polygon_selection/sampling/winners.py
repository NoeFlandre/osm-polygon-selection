"""Per-cell reservoir winner selection across a parquet file.

The algorithm: open the file once, walk each row group, assign
each row to a grid cell, and within each cell pick the row
whose ``uniform(0, 1) * n_seen_so_far`` is maximal. Then fetch
the winning rows in a second pass over the same ParquetFile.

The weighted-reservoir formulation is equivalent to a uniform
random draw per cell without replacement.
"""

from __future__ import annotations

import random
from collections import defaultdict
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

from osm_polygon_selection.sampling.config import ALL_COLS, GEO_COLS


def _assign_cells(
    lons_np: np.ndarray,
    lats_np: np.ndarray,
    K: int,
    min_lon: float,
    min_lat: float,
    lon_step: float,
    lat_step: float,
    valid_mask: np.ndarray,
) -> np.ndarray:
    ix_f = np.floor((lons_np - min_lon) / lon_step).astype(np.int64)
    iy_f = np.floor((lats_np - min_lat) / lat_step).astype(np.int64)
    ix_f = np.clip(ix_f, 0, K - 1)
    iy_f = np.clip(iy_f, 0, K - 1)
    flat_cells = ix_f * K + iy_f
    return flat_cells[valid_mask]


def pick_and_fetch(
    pq_file: Path,
    K: int,
    min_lon: float,
    min_lat: float,
    lon_step: float,
    lat_step: float,
    rng: random.Random,
) -> dict[tuple[int, int], dict]:
    """Single pass: per-cell reservoir winner selection AND row fetch.

    The file is opened exactly once.
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
        valid_flat = _assign_cells(
            lons_np, lats_np, K, min_lon, min_lat, lon_step, lat_step, valid_mask,
        )
        if len(valid_flat) == 0:
            continue
        unique_cells, inv = np.unique(valid_flat, return_inverse=True)
        prev_counts = np.array(
            [cell_count.get((ck // K, ck % K), 0) for ck in unique_cells.tolist()],
            dtype=np.int64,
        )
        rg_counts = np.bincount(inv, minlength=len(unique_cells))
        rng_np = np.random.default_rng(rng.randrange(2**63))
        rand_u_per_row = rng_np.uniform(0.0, 1.0, size=len(valid_flat))
        ranks = np.empty(len(valid_flat), dtype=np.int64)
        for j in range(len(unique_cells)):
            ix_j = np.where(inv == j)[0]
            ranks[ix_j] = np.arange(1, len(ix_j) + 1)
        n_seen_combined = prev_counts[inv] + ranks
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
            cell_count[cell] = int(prev_counts[j]) + int(rg_counts[j])
            orig_idx = int(valid_orig_idx[int(winner_within_valid[j])])
            if cell not in winner_global_idx:
                winner_global_idx[cell] = (rg, orig_idx)

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


__all__ = ["pick_and_fetch"]

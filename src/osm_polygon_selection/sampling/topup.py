"""Top-up: uniform random draw if the grid came up short.

Used when the grid's per-cell reservoir winners don't reach
``target_n`` (very sparse or linear countries where many grid
cells are empty). The top-up draws from the full parquet and
appends to the existing sample in deterministic draw order.
"""

from __future__ import annotations

import random
from pathlib import Path

import pyarrow.parquet as pq

from osm_polygon_selection.sampling.config import ALL_COLS


def top_up(
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


__all__ = ["top_up"]

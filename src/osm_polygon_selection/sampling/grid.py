"""Grid sampling facade.

Combines bbox scan + per-cell reservoir winner selection +
top-up into the public :func:`grid_sample_country`.

The algorithm:
1. Single-pass bbox scan (compute_bbox)
2. Bucket each centroid into a K x K grid where K = ceil(sqrt(target_n))
3. Pick a uniform random representative per cell (reservoir of size 1)
4. Top-up with a uniform random sample if grid came up short

All randomness goes through the caller's ``rng`` (a
``random.Random`` instance). No global numpy state.
"""

from __future__ import annotations

import math
import random
from pathlib import Path

from osm_polygon_selection.sampling.bbox import compute_bbox
from osm_polygon_selection.sampling.topup import top_up
from osm_polygon_selection.sampling.winners import pick_and_fetch


def grid_sample_country(
    pq_file: Path,
    target_n: int,
    rng: random.Random,
) -> list[dict]:
    """Sample ``target_n`` polygons spread geographically across the country."""
    K = max(1, math.ceil(math.sqrt(target_n)))

    min_lon, min_lat, max_lon, max_lat, n_total = compute_bbox(pq_file)
    if n_total == 0:
        return []

    lon_step = (max_lon - min_lon) / K if max_lon > min_lon else 1e-9
    lat_step = (max_lat - min_lat) / K if max_lat > min_lat else 1e-9

    cell_record = pick_and_fetch(
        pq_file, K, min_lon, min_lat, lon_step, lat_step, rng
    )

    sampled = [cell_record[c] for c in sorted(cell_record.keys())]

    if len(sampled) < target_n:
        sampled = top_up(pq_file, sampled, target_n, rng)

    return sampled[:target_n]


__all__ = ["grid_sample_country"]

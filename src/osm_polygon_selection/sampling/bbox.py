"""Bounding-box scan over a parquet file.

Single-pass scan that returns ``(min_lon, min_lat, max_lon,
max_lat, n_total)``. Handles NaN coordinates by skipping them.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

from osm_polygon_selection.sampling.config import GEO_COLS


def compute_bbox(pq_file: Path) -> tuple[float, float, float, float, int]:
    """Single-pass bbox scan over ``pq_file``.

    Returns ``(min_lon, min_lat, max_lon, max_lat, n_total)``.
    Empty row groups do not move the bbox.
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


__all__ = ["compute_bbox"]

"""Map bounds computation.

Two related concerns:

- :func:`default_center` returns the fallback map center used when
  the JSONL is empty (Switzerland).
- :func:`compute_fit_bounds` returns ``fit_bounds`` arguments
  computed from a robust 5th..95th percentile of the per-row
  coordinates. Robust to outliers like France's overseas
  territories (lon -60, lat -21) that would otherwise drag the
  map to fit the whole globe.
"""

from __future__ import annotations

from typing import Iterable

from osm_polygon_selection.visualization.rows import extract_centroid


# Switzerland (lon, lat) — the empty-input fallback.
DEFAULT_CENTER_LONLAT: tuple[float, float] = (9.5, 47.0)
DEFAULT_ZOOM = 4


def default_center() -> tuple[list[float], int]:
    """Return ``(center_latlon, zoom)`` for an empty JSONL."""
    return [DEFAULT_CENTER_LONLAT[1], DEFAULT_CENTER_LONLAT[0]], DEFAULT_ZOOM


def compute_fit_bounds(
    rows: Iterable[dict],
) -> list[list[float]] | None:
    """Compute robust fit-bounds for a folium.Map.

    Returns ``[[min_lat, min_lon], [max_lat, max_lon]]`` with 5%
    padding so points don't get clipped at the edge. Returns
    None if no rows have usable coordinates.
    """
    lons: list[float] = []
    lats: list[float] = []
    for row in rows:
        c = extract_centroid(row)
        if c is None:
            continue
        lon, lat = c
        lons.append(lon)
        lats.append(lat)
    if not lons or not lats:
        return None

    lons_sorted = sorted(lons)
    lats_sorted = sorted(lats)
    n = len(lons_sorted)
    lo_idx = max(0, int(n * 0.05))
    hi_idx = min(n - 1, int(n * 0.95))
    min_lon, max_lon = lons_sorted[lo_idx], lons_sorted[hi_idx]
    min_lat, max_lat = lats_sorted[lo_idx], lats_sorted[hi_idx]
    lon_pad = max((max_lon - min_lon) * 0.05, 0.5)
    lat_pad = max((max_lat - min_lat) * 0.05, 0.5)
    return [
        [min_lat - lat_pad, min_lon - lon_pad],
        [max_lat + lat_pad, max_lon + lon_pad],
    ]


__all__ = [
    "DEFAULT_CENTER_LONLAT",
    "DEFAULT_ZOOM",
    "compute_fit_bounds",
    "default_center",
]

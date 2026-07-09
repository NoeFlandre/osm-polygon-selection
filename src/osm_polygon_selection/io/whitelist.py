"""Whitelist I/O + matched_tag computation.

The whitelist is a flat JSON list of OSM ``key=value`` strings used
by Stage 2 to filter polygons. We load it once at module level
(``_WHITELIST_CACHE``) and reuse across calls.

:func:`compute_matched_tag` returns the first ``key=value`` from a
row's ``tags`` that hits the whitelist, or the row's existing
``matched_tag`` if already set (pre-populated by Stage 2 for newer
countries).
"""

from __future__ import annotations

import json
from pathlib import Path

# Default whitelist location (external HDD).
DEFAULT_WHITELIST_PATH = Path("/Volumes/Seagate M3/osm-polygon-selection/whitelist.json")

# Module-level cache. ``load_whitelist`` returns this if set;
# ``clear_whitelist_cache`` resets it (useful in tests).
_WHITELIST_CACHE: set[str] | None = None
_WHITELIST_CACHE_PATH: Path | None = None


def load_whitelist(path: Path = DEFAULT_WHITELIST_PATH) -> set[str]:
    """Load the whitelist as a set, caching at module level.

    Re-loading is a no-op unless ``clear_whitelist_cache`` is called
    first (or the path argument changes).
    """
    global _WHITELIST_CACHE, _WHITELIST_CACHE_PATH
    if _WHITELIST_CACHE is not None and _WHITELIST_CACHE_PATH == path:
        return _WHITELIST_CACHE
    with path.open() as f:
        _WHITELIST_CACHE = set(json.load(f))
    _WHITELIST_CACHE_PATH = path
    return _WHITELIST_CACHE


def clear_whitelist_cache() -> None:
    """Reset the module-level whitelist cache (testing only)."""
    global _WHITELIST_CACHE, _WHITELIST_CACHE_PATH
    _WHITELIST_CACHE = None
    _WHITELIST_CACHE_PATH = None


def compute_matched_tag(row: dict, whitelist_path: Path = DEFAULT_WHITELIST_PATH) -> str:
    """Return the first tag in row.tags that hits the whitelist.

    If the row already has a ``matched_tag`` set (newer countries
    whose Stage 2 populated it), return that. Otherwise scan
    ``row.tags`` and return the first ``key=value`` string present
    in the whitelist, or "" if no match.
    """
    existing = row.get("matched_tag")
    if existing:
        return str(existing)
    wl = load_whitelist(whitelist_path)
    for t in row.get("tags", []):
        if t in wl:
            return str(t)
    return ""


def vectorized_compute_matched_tags(
    tags_array,
    whitelist_path: Path = DEFAULT_WHITELIST_PATH,
):
    """Vectorized "first whitelist hit per list" using pyarrow.

    Accepts a ``pyarrow.Array`` or ``ChunkedArray`` of ``list<string>``.
    Returns a ``pyarrow.Array`` of ``string`` with the same length,
    where element ``i`` is the first ``key=value`` in ``tags_array[i]``
    that is in the whitelist, or ``""`` if no match.

    Implementation: flatten the list-of-strings to a flat string array,
    run ``pc.is_in`` against the whitelist (single C-level pass), then
    for each row compute the index of the first ``True`` value via
    ``np.argmax`` on the boolean row-slices. This is O(N + M) where
    N = total tags, M = rows, and is dramatically faster than the
    Python-row-by-row version (~10-50x for >1M rows).
    """
    import numpy as np
    import pyarrow as pa
    from osm_polygon_selection.io.pyarrow_compat import is_in as _is_in

    wl = load_whitelist(whitelist_path)
    wl_set = frozenset(wl)
    if not wl_set:
        # Empty whitelist: every row returns "".
        return pa.array([""] * len(tags_array), type=pa.string())

    # Build a pa.array of the whitelist for the C-level is_in.
    wl_array = pa.array(sorted(wl_set), type=pa.string())

    out_chunks = []
    chunks = tags_array.chunks if hasattr(tags_array, "chunks") else [tags_array]
    for chunk in chunks:
        # chunk is list<string>. Flatten the strings, run is_in.
        flat_strs = chunk.flatten()
        flat_mask = _is_in(flat_strs, wl_array)
        offsets = chunk.offsets.to_numpy()
        flat_np = np.asarray(flat_mask)  # bool array, len = total tags
        flat_strs_np = np.asarray(flat_strs)

        # For each row i, the first match is the position of the first
        # True in flat_np[offsets[i]:offsets[i+1]]. Vectorize this:
        #   1. build a per-tag position index [0, 1, 2, ..., n_flat-1]
        #   2. "hide" non-matches with a large sentinel (n_flat)
        #   3. take the min over each row's slice
        n_flat = len(flat_np)
        n_rows = len(chunk)
        if n_flat == 0:
            out_chunks.append(pa.array([""] * n_rows, type=pa.string()))
            continue

        hidden = np.where(flat_np, np.arange(n_flat), n_flat + 1)
        # Per-row min over [offsets[i]:offsets[i+1]] = first True position.
        n_rows = len(chunk)
        row_first = np.full(n_rows, n_flat + 1, dtype=np.int64)
        non_empty_idx = np.where(offsets[1:] > offsets[:-1])[0]
        if len(non_empty_idx) > 0:
            starts = offsets[:-1][non_empty_idx]
            row_first[non_empty_idx] = np.minimum.reduceat(hidden, starts)
        matched = row_first <= n_flat
        out_per_row = [""] * n_rows
        if matched.any():
            idxs = row_first[matched]
            out_per_row_arr = np.empty(matched.sum(), dtype=object)
            out_per_row_arr[:] = flat_strs_np[idxs]
            out_per_row = [""] * n_rows
            for j, i in enumerate(np.where(matched)[0]):
                out_per_row[int(i)] = str(out_per_row_arr[j])
        out_chunks.append(pa.array(out_per_row, type=pa.string()))
    if len(out_chunks) == 1:
        return out_chunks[0]
    return pa.chunked_array(out_chunks)


__all__ = [
    "DEFAULT_WHITELIST_PATH",
    "clear_whitelist_cache",
    "compute_matched_tag",
    "load_whitelist",
    "vectorized_compute_matched_tags",
]

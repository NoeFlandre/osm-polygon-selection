"""Whitelist I/O + matched_tag computation.

The whitelist is a flat JSON list of OSM ``key=value`` strings used
by Stage 2 to filter polygons. We load it once at module level
(``_WHITELIST_CACHE``) and reuse across calls.

``compute_matched_tag`` returns the first ``key=value`` from a row's
``tags`` that hits the whitelist, or the row's existing
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

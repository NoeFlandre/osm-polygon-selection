"""Cached loader for the OSM tag whitelist.

Loads the JSON list of ``key=value`` strings into a ``set`` once
per path, then reuses the cached value. The cache is keyed by
path so the runner can be re-run with a different config
without stale data.
"""

from __future__ import annotations

import json
from pathlib import Path

_CACHE: dict[Path, set[str]] = {}


def load_whitelist(path: Path) -> set[str]:
    """Load the whitelist at ``path`` as a Python ``set`` (cached)."""
    if path in _CACHE:
        return _CACHE[path]
    with path.open() as f:
        _CACHE[path] = set(json.load(f))
    return _CACHE[path]


def reset_cache() -> None:
    """Clear the in-memory whitelist cache (for tests)."""
    _CACHE.clear()

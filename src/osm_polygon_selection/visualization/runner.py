"""CLI entry-point constants for ``scripts/visualize.py``.

The default --limit is set high enough to cover the current sample
(~16k polygons across 284 countries). With 5000 many small
countries (south sudan, marshall-islands, samoa, etc.) got
truncated and disappeared from the map. 25000 leaves headroom
for future dataset growth without truncating any country.
"""

from __future__ import annotations

MAX_DEFAULT_LIMIT = 25000


__all__ = ["MAX_DEFAULT_LIMIT"]

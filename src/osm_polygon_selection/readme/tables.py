"""Markdown table renderers used by the README package.

The canonical home of :func:`build_country_table`. The root-level
``osm_polygon_selection.country_table`` is a thin backwards-compat
facade re-exporting this.
"""

from __future__ import annotations


def build_country_table(countries: list[dict]) -> str:
    """Render a markdown table with one row per country.

    Each input dict must have:
      - ``country``: country name (str)
      - ``n_polygons``: polygon count (int)
      - ``extract_status``: ``"clean"`` or ``"killed"`` (str)

    Output is a markdown table with columns: Country, Polygons,
    Status. Rows are sorted alphabetically by country name. A
    ``**Total**`` row with the sum of polygons is appended at the
    end. Works with empty input (returns header + 0-total row).
    """
    lines = [
        "| Country | Polygons | Status |",
        "|---------|----------|--------|",
    ]
    total = 0
    for c in sorted(countries, key=lambda x: x["country"]):
        lines.append(f"| {c['country']} | {c['n_polygons']:,} | {c['extract_status']} |")
        total += c["n_polygons"]
    lines.append(f"| **Total** | {total:,} | |")
    return "\n".join(lines)


__all__ = ["build_country_table"]

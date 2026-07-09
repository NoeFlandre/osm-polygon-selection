"""Folium map rendering.

Two helpers:

- :func:`build_popup_html` assembles the popup HTML for one
  CircleMarker (osm_id, area, country, size_bin, tags).
- :func:`render_map` builds the full folium.Map from a JSONL
  path, applies the color palette, plots CircleMarkers, and
  writes the HTML file.
"""

from __future__ import annotations

from pathlib import Path

import folium

from osm_polygon_selection.visualization.bounds import (
    compute_fit_bounds,
    default_center,
)
from osm_polygon_selection.visualization.colors import color_for_country
from osm_polygon_selection.visualization.rows import (
    collect_countries,
    extract_centroid,
    load_rows,
)


def build_popup_html(row: dict) -> str:
    """Assemble the popup HTML for a single row."""
    tags = ", ".join(row.get("tags", [])[:5])
    country_str = (
        f"<br>country: {row['country']}" if row.get("country") else ""
    )
    return (
        f"osm_id={row['osm_id']}"
        f"<br>area={row['area_km2']:.3f} km²"
        f"{country_str}"
        f"<br>size_bin: {row.get('size_bin', '?')}"
        f"<br>tags: {tags}"
    )


def _marker_radius(area: float) -> float:
    """Compute the CircleMarker radius in pixels from area_km2."""
    return max(2, min(15, (area ** 0.5) * 1.5))


def render_map(jsonl_path: Path, out_path: Path, limit: int) -> int:
    """Render ``jsonl_path`` to ``out_path`` (HTML), plot ``limit`` rows.

    Returns the number of polygons actually plotted.
    """
    rows = load_rows(jsonl_path, limit=limit)
    countries_seen = collect_countries(rows)
    country_to_color: dict[str, str] = {}
    for cc in sorted(countries_seen):
        color_for_country(cc, country_to_color)

    if rows:
        first = rows[0]
        first_c = extract_centroid(first)
        if first_c is not None:
            center = [first_c[1], first_c[0]]
            zoom = 4
        else:
            center, zoom = default_center()
    else:
        center, zoom = default_center()

    fmap = folium.Map(location=center, zoom_start=zoom)

    bounds = compute_fit_bounds(rows)
    if bounds is not None:
        fmap.fit_bounds(bounds)

    n_plotted = 0
    for row in rows:
        country = row.get("country")
        color = color_for_country(country, country_to_color)
        popup = folium.Popup(build_popup_html(row), max_width=300)
        c = extract_centroid(row)
        if c is None:
            continue
        lon, lat = c
        area = row.get("area_km2", 0.1)
        folium.CircleMarker(
            location=[lat, lon],
            radius=_marker_radius(area),
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.5,
            weight=1,
            popup=popup,
        ).add_to(fmap)
        n_plotted += 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fmap.save(str(out_path))
    return n_plotted


__all__ = ["build_popup_html", "render_map"]

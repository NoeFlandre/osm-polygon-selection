"""Folium-based interactive HTML map rendering.

Public API:

- :func:`color_for_country` (colors): stable color per country.
- :func:`load_rows` (rows): read JSONL into a list of row dicts.
- :func:`extract_centroid` (rows): accept both flat and nested formats.
- :func:`compute_fit_bounds` (bounds): robust 5th..95th percentile bbox.
- :func:`default_center` (bounds): Switzerland fallback.
- :func:`build_popup_html` (render): assemble the popup text.
- :func:`render_map` (render): full folium.Map from a JSONL path.
- :func:`MAX_DEFAULT_LIMIT` (runner): CLI default for ``--limit``.

CLI: ``scripts/visualize.py`` is a thin wrapper around
:func:`render_map`.
"""

from osm_polygon_selection.visualization.bounds import (
    compute_fit_bounds,
    default_center,
)
from osm_polygon_selection.visualization.colors import (
    COUNTRY_COLORS,
    color_for_country,
)
from osm_polygon_selection.visualization.render import (
    build_popup_html,
    render_map,
)
from osm_polygon_selection.visualization.rows import (
    extract_centroid,
    load_rows,
)
from osm_polygon_selection.visualization.runner import MAX_DEFAULT_LIMIT

__all__ = [
    "COUNTRY_COLORS",
    "MAX_DEFAULT_LIMIT",
    "build_popup_html",
    "color_for_country",
    "compute_fit_bounds",
    "default_center",
    "extract_centroid",
    "load_rows",
    "render_map",
]

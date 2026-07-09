"""Stable color assignment per country.

The visualization cycles through a fixed 16-color palette in the
order the country was first seen, but the *first* allocation is
deterministic: we pre-assign colors to the sorted set of countries
so the same dataset always renders with the same colors.
"""

from __future__ import annotations

COUNTRY_COLORS: list[str] = [
    "#e41a1c",  # red
    "#377eb8",  # blue
    "#4daf4a",  # green
    "#984ea3",  # purple
    "#ff7f00",  # orange
    "#ffff33",  # yellow
    "#a65628",  # brown
    "#f781bf",  # pink
    "#1b9e77",  # teal
    "#d95f02",  # dark orange
    "#7570b3",  # dark purple
    "#e7298a",  # dark pink
    "#66a61e",  # olive
    "#a6cee3",  # light blue
    "#fdbf6f",  # peach
    "#b2df8a",  # light green
]

DEFAULT_FOLIUM_BLUE = "#3388ff"


def color_for_country(
    country: str | None,
    country_to_color: dict[str, str],
) -> str:
    """Return a stable hex color for the given country.

    If ``country`` is None, returns the default folium blue.
    Otherwise: if the country already has a color in
    ``country_to_color`` (built deterministically from the sorted
    set of countries), returns it; otherwise allocates the next
    color in :data:`COUNTRY_COLORS` and records it.
    """
    if country is None:
        return DEFAULT_FOLIUM_BLUE
    if country not in country_to_color:
        country_to_color[country] = COUNTRY_COLORS[
            len(country_to_color) % len(COUNTRY_COLORS)
        ]
    return country_to_color[country]


__all__ = ["COUNTRY_COLORS", "DEFAULT_FOLIUM_BLUE", "color_for_country"]

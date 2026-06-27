"""Render a JSONL of polygons to an interactive HTML map.

Color-codes by country if the row has a 'country' field (set by
sample_for_map.py), or by continent if 'continent' is present, or
defaults to blue.
"""

import argparse
import json
from pathlib import Path

import folium

# Stable, distinct color per country (cycled). Chosen for legibility
# on the default folium tileset.
COUNTRY_COLORS = [
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


def color_for_country(country: str | None, country_to_color: dict[str, str]) -> str:
    if country is None:
        return "#3388ff"  # default folium blue
    if country not in country_to_color:
        country_to_color[country] = COUNTRY_COLORS[
            len(country_to_color) % len(COUNTRY_COLORS)
        ]
    return country_to_color[country]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl", type=Path, help="Path to .jsonl file")
    parser.add_argument("out", type=Path, help="Path to output .html file")
    parser.add_argument("--limit", type=int, default=2000, help="Max polygons to plot")
    args = parser.parse_args()

    # First pass: count countries for color assignment.
    countries_seen: set[str] = set()
    rows_buffer: list[dict] = []
    with args.jsonl.open() as f:
        for line in f:
            row = json.loads(line)
            rows_buffer.append(row)
            if "country" in row and row["country"]:
                countries_seen.add(row["country"])
            if len(rows_buffer) >= args.limit:
                break

    country_to_color = {c: COUNTRY_COLORS[i % len(COUNTRY_COLORS)]
                        for i, c in enumerate(sorted(countries_seen))}

    # Use the centroid of the first row as the initial map center.
    if rows_buffer:
        first = rows_buffer[0]
        c = first["centroid"]
        center = [c[1], c[0]]  # folium wants [lat, lon]
        zoom = 4
    else:
        center, zoom = [47.0, 9.5], 4

    fmap = folium.Map(location=center, zoom_start=zoom)

    for row in rows_buffer:
        country = row.get("country")
        color = color_for_country(country, country_to_color)
        tags = ", ".join(row.get("tags", [])[:5])
        country_str = f"<br>country: {country}" if country else ""
        popup = (
            f"osm_id={row['osm_id']}"
            f"<br>area={row['area_km2']:.3f} km²"
            f"{country_str}"
            f"<br>size_bin: {row.get('size_bin', '?')}"
            f"<br>tags: {tags}"
        )
        # Use a CircleMarker sized by area, centered on the polygon
        # centroid. Cheaper than GeoJson polygons and scales nicely
        # on the map.
        if "centroid" in row:
            lon, lat = row["centroid"]
            area = row.get("area_km2", 0.1)
            # radius in pixels: sqrt(area) * scale, clamped
            radius = max(2, min(15, (area ** 0.5) * 1.5))
            folium.CircleMarker(
                location=[lat, lon],
                radius=radius,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.5,
                weight=1,
                popup=folium.Popup(popup, max_width=300),
            ).add_to(fmap)

    # Add a small legend if any countries are colored.
    if country_to_color:
        legend_html = (
            "<div style='position:fixed; bottom:20px; left:20px; "
            "background:white; padding:8px; border:1px solid grey; "
            "z-index:1000; font-size:11px;'>"
            "<b>Country</b><br>"
        )
        for c, col in sorted(country_to_color.items()):
            legend_html += f"<span style='color:{col}'>■</span> {c}<br>"
        legend_html += "</div>"
        fmap.get_root().add_child(folium.Element(legend_html))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fmap.save(str(args.out))
    print(f"plotted {len(rows_buffer)} polygons ({len(country_to_color)} countries) to {args.out}")


if __name__ == "__main__":
    main()

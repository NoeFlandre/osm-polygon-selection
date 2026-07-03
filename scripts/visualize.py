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

# Default --limit. Set high enough to cover the current sample
# (4418 polygons, growing) plus a safety margin. The previous
# default of 2000 truncated to ~10 alphabetically-first countries,
# making Spain, Portugal, Turkey, Greece, Sweden, Norway, Finland,
# Ukraine, etc. invisible on the rendered map. 5000 covers the
# current sample with margin; bump if the sample grows.
MAX_DEFAULT_LIMIT = 5000


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
    parser.add_argument("--limit", type=int, default=MAX_DEFAULT_LIMIT, help="Max polygons to plot")
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

    country_to_color = {cc: COUNTRY_COLORS[i % len(COUNTRY_COLORS)]
                        for i, cc in enumerate(sorted(countries_seen))}

    # Use the centroid of the first row as the initial map center.
    # Accept both formats: nested centroid list OR flat lon/lat fields.
    if rows_buffer:
        first = rows_buffer[0]
        if "centroid_lon" in first and "centroid_lat" in first:
            c = [first["centroid_lon"], first["centroid_lat"]]
        else:
            c = first.get("centroid", [9.5, 47.0])  # fallback: Switzerland
        center = [c[1], c[0]]  # folium wants [lat, lon]
        zoom = 4
    else:
        center, zoom = [47.0, 9.5], 4

    fmap = folium.Map(location=center, zoom_start=zoom)

    # If the sample spans a wide geographic area, auto-fit the bounds
    # so all polygons are visible (not just the first one). We compute
    # the bbox from a robust percentile (5th..95th) to avoid outliers
    # like France's overseas territories (lon -60, lat -21) pulling
    # the map to fit the whole globe.
    if rows_buffer:
        lons = []
        lats = []
        for row in rows_buffer:
            if "centroid_lon" in row and "centroid_lat" in row:
                lon, lat = row["centroid_lon"], row["centroid_lat"]
            elif "centroid" in row:
                lon, lat = row["centroid"]
            else:
                continue
            if lon is None or lat is None:
                continue
            lons.append(lon)
            lats.append(lat)
        if lons and lats:
            lons_sorted = sorted(lons)
            lats_sorted = sorted(lats)
            n = len(lons_sorted)
            # 5th and 95th percentile bounds (robust to outliers).
            lo_idx = max(0, int(n * 0.05))
            hi_idx = min(n - 1, int(n * 0.95))
            min_lon, max_lon = lons_sorted[lo_idx], lons_sorted[hi_idx]
            min_lat, max_lat = lats_sorted[lo_idx], lats_sorted[hi_idx]
            # 5% padding so points don't get clipped at the edge.
            lon_pad = max((max_lon - min_lon) * 0.05, 0.5)
            lat_pad = max((max_lat - min_lat) * 0.05, 0.5)
            fmap.fit_bounds(
                [
                    [min_lat - lat_pad, min_lon - lon_pad],
                    [max_lat + lat_pad, max_lon + lon_pad],
                ]
            )

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
        # on the map. Accept both formats:
        # - new (parquet): centroid_lon + centroid_lat
        # - old (JSONL): centroid = [lon, lat]
        if "centroid_lon" in row and "centroid_lat" in row:
            lon, lat = row["centroid_lon"], row["centroid_lat"]
        elif "centroid" in row:
            lon, lat = row["centroid"]
        else:
            continue  # no coordinates, skip
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

    # Build the legend HTML (we'll inject it after folium save, since
    # folium 0.20's get_root().add_child(Element) silently drops the
    # element from the rendered output).
    legend_html: str = ""
    if country_to_color:
        legend_html = (
            "<div style='position:fixed; bottom:20px; left:20px; "
            "background:white; padding:8px; border:1px solid grey; "
            "z-index:1000; font-size:11px; max-width:280px;'>"
            "<b>Sampled for visualization (not exhaustive)</b><br>"
            f"Showing ~{len(rows_buffer)} representative polygons "
            "(~1 per K&times;K grid cell per country, power-law "
            "weighted). See combined/all_world.parquet for the full "
            "dataset.<br>"
            "<br>"
            "<b>Country</b><br>"
        )
        for cc, col in sorted(country_to_color.items()):
            legend_html = legend_html + f"<span style='color:{col}'>■</span> {cc}<br>"
        legend_html = legend_html + "</div>"

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fmap.save(str(args.out))

    # Inject the legend into the saved HTML by appending it just
    # before </body>. This is more reliable than folium's
    # add_child for plain HTML overlays in newer folium versions.
    if legend_html:
        with args.out.open() as f:
            html = f.read()
        if "</body>" in html:
            html = html.replace("</body>", legend_html + "</body>", 1)
            with args.out.open("w") as f:
                f.write(html)

    print(f"plotted {len(rows_buffer)} polygons ({len(country_to_color)} countries) to {args.out}")


if __name__ == "__main__":
    main()

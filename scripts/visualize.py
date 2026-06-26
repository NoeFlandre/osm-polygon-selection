"""Render a JSONL of polygons to an interactive HTML map."""

import argparse
import json
from pathlib import Path

import folium
import shapely.wkt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl", type=Path, help="Path to .jsonl file")
    parser.add_argument("out", type=Path, help="Path to output .html file")
    parser.add_argument("--limit", type=int, default=2000, help="Max polygons to plot")
    args = parser.parse_args()

    fmap = folium.Map(location=[47.0, 9.5], zoom_start=10)

    count = 0
    with args.jsonl.open() as f:
        for line in f:
            if count >= args.limit:
                break
            row = json.loads(line)
            geom = shapely.wkt.loads(row["geometry"])
            tags = ", ".join(row["tags"][:5])
            popup = f"osm_id={row['osm_id']}<br>area={row['area_km2']:.3f} km²<br>tags: {tags}"
            gj = folium.GeoJson(
                geom.__geo_interface__,
                style_function=lambda _: {"color": "blue", "weight": 1, "fillOpacity": 0.3},
            )
            gj.add_child(folium.Popup(popup, max_width=300))
            gj.add_to(fmap)
            count += 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fmap.save(str(args.out))
    print(f"plotted {count} polygons to {args.out}")


if __name__ == "__main__":
    main()

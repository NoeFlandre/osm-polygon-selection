"""Full-row example markdown table renderer.

Used by the dataset README to display one representative row's
full set of columns (the sample JSONL only carries the centroid
columns).
"""

from __future__ import annotations

from pathlib import Path

from osm_polygon_selection.sample_tables.formatting import truncate
from osm_polygon_selection.sample_tables.lookup import (
    fetch_full_row_from_parquet,
    pick_sample_row,
)


def _format_cell(name: str, value: object) -> str:
    if value is None:
        return "*(none)*"
    if name == "area_km2" and isinstance(value, (int, float)):
        return f"{value:.4f}"
    if name == "tags" and isinstance(value, list):
        return "<br>".join(f"`{t}`" for t in value) if value else "*(none)*"
    if name == "geometry_wkt" and isinstance(value, str):
        return f"`{truncate(value, 100)}`"
    if name in ("centroid_lon", "centroid_lat") and isinstance(value, (int, float)):
        return f"{value:.6f}"
    return f"`{value}`"


def build_example_row_table(
    sample_path: Path,
    fallback_dir: Path | None = None,
    sample_row: dict | None = None,
) -> str:
    """Render a markdown table showing all columns of one row."""
    if sample_row is None:
        sample_row = pick_sample_row(sample_path)
    if sample_row is None:
        return (
            "*(no sample row available - run `scripts/sample_for_map.py` "
            "to generate `sample/sample_map.jsonl`)*\n"
        )

    full_row = sample_row
    if fallback_dir is not None:
        country = sample_row.get("country")
        osm_id = sample_row.get("osm_id")
        if country and osm_id is not None:
            pq_path = (
                fallback_dir / "per_country" / country / f"{country}.parquet"
            )
            fetched = fetch_full_row_from_parquet(pq_path, int(osm_id))
            if fetched is not None:
                full_row = fetched

    cols = [
        ("osm_id", full_row.get("osm_id")),
        ("osm_type", full_row.get("osm_type")),
        ("centroid_lon", full_row.get("centroid_lon")),
        ("centroid_lat", full_row.get("centroid_lat")),
        ("area_km2", full_row.get("area_km2")),
        ("tags", full_row.get("tags")),
        ("matched_tag", full_row.get("matched_tag")),
        ("continent", full_row.get("continent")),
        ("size_bin", full_row.get("size_bin")),
        ("country", full_row.get("country")),
        ("extract_status", full_row.get("extract_status")),
        ("pbf_date", full_row.get("pbf_date")),
        ("geometry_wkt", full_row.get("geometry_wkt")),
    ]
    out = "| column | value |\n|--------|-------|\n"
    for name, value in cols:
        out += f"| {name} | {_format_cell(name, value)} |\n"
    return out


__all__ = ["build_example_row_table"]

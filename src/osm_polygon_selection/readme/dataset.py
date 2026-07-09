"""Root README rendering for the build_dataset pipeline.

The "pre-organize" form of the dataset root README, written by
``scripts/build_dataset.py``. Differs from
``readme.root.build_root_readme`` (the "post-organize" form
written by ``scripts/organize_dataset.py``) in three ways:
- uses a flat (non-nested) layout string
- embeds schema column descriptions in-line (not from manifest)
- embeds the example row pulled from the sample JSONL with a
  fallback to the per-country parquet
- substitutes ``build_country_table(clean_countries)`` at format
  time

The big body template lives in
``readme.templates.DATASET_README_BODY`` so this module can
stay focused on the data plumbing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping

from osm_polygon_selection.readme.tables import build_country_table
from osm_polygon_selection.readme.templates import (
    DATASET_README_BODY,
    YAML_FRONTMATTER,
)
from osm_polygon_selection.sample_tables import (
    build_example_row_table,
    build_size_bin_distribution_table,
    compute_global_size_bin_distribution,
)

__all__ = ["write_readme", "render_dataset_readme"]


def write_readme(
    out_dir: Path,
    countries_done: Iterable[Mapping],
    total_polygons: int,
    *,
    pipeline_version: str,
    git_sha_value: str,
    built_at: str,
    geometry_encoding: str,
) -> None:
    """Write the dataset's root README.md to ``out_dir``.

    The README is byte-exact equivalent to the prior in-script
    implementation. The parameters capture every piece of
    module-level state the in-script function used to read.
    """
    readme = render_dataset_readme(
        out_dir=out_dir,
        countries_done=countries_done,
        total_polygons=total_polygons,
        pipeline_version=pipeline_version,
        git_sha_value=git_sha_value,
        built_at=built_at,
        geometry_encoding=geometry_encoding,
    )
    (out_dir / "README.md").write_text(readme)
    print(f"README.md written ({len(readme)} chars)")


def _schema_table(geometry_encoding: str) -> str:
    """Build the schema markdown table with the given geometry encoding."""
    schema_columns = [
        ("osm_id", "int64", "OSM object id"),
        ("osm_type", "string", '"way" or "relation"'),
        ("centroid_lon", "float64", "polygon centroid longitude (WGS84)"),
        ("centroid_lat", "float64", "polygon centroid latitude (WGS84)"),
        ("area_km2", "float64", "polygon area in km² (Web Mercator, accurate at mid-latitudes)"),
        ("tags", "list(string)", "OSM `key=value` tags"),
        ("matched_tag", "string", "the first tag in `tags` that hit the whitelist filter (the reason the polygon survived)"),
        ("continent", "string", "Natural Earth admin0 lookup of the centroid"),
        ("size_bin", "string", '"small" (0.1-1), "medium" (1-10), or "large" (10-100) km²'),
        ("country", "string", "ISO-style country name"),
        ("extract_status", "string", '"clean" (extract process ran to completion) or "killed" (extract was interrupted before completion)'),
        ("pbf_date", "string", "date of the source PBF file (from mtime)"),
    ]
    if geometry_encoding == "wkt":
        schema_columns.append((
            "geometry_wkt", "string",
            "**polygon geometry as WKT** (WGS84, well-known text). "
            "Parse with `shapely.wkt.loads(row.geometry_wkt)`. "
            "Default encoding; size of the combined parquet scales "
            "with polygon complexity (~3-5x larger than centroid-only)."
        ))
    elif geometry_encoding == "wkb":
        schema_columns.append((
            "geometry_wkb", "binary",
            "**polygon geometry as WKB** (WGS84, well-known binary). "
            "Parse with `shapely.wkt.loads(row.geometry_wkb)`. "
            "Smaller than WKT (~50% smaller) at the cost of being binary."
        ))

    table = "| column | type | description |\n|--------|------|-------------|\n"
    for name, dtype, desc in schema_columns:
        table += f"| {name} | {dtype} | {desc} |\n"
    return table


def render_dataset_readme(
    out_dir: Path,
    countries_done: Iterable[Mapping],
    total_polygons: int,
    *,
    pipeline_version: str,
    git_sha_value: str,
    built_at: str,
    geometry_encoding: str,
) -> str:
    """Render the dataset root README content as a string (no I/O).

    Splitting this from ``write_readme`` lets tests assert byte-exact
    output without writing to disk.
    """
    countries_list: list[dict] = list(countries_done)  # type: ignore[arg-type]
    clean_countries: list[dict] = [c for c in countries_list if c.get("extract_status") == "clean"]

    schema_table = _schema_table(geometry_encoding)

    sample_path = out_dir / "sample" / "sample_map.jsonl"
    if not sample_path.is_file():
        sample_path = Path("/tmp/sample_map.jsonl")
    sample_dist = compute_global_size_bin_distribution(out_dir)
    size_bin_table = build_size_bin_distribution_table(sample_dist)
    example_row_table = build_example_row_table(
        sample_path, fallback_dir=out_dir
    )
    sample_n_polygons = sum(n for _, n, _ in sample_dist)

    return YAML_FRONTMATTER + DATASET_README_BODY.format(
        n_countries=len(clean_countries),
        total_polygons=total_polygons,
        schema_table=schema_table,
        pipeline_version=pipeline_version,
        git_sha_value=git_sha_value,
        built_at=built_at,
        size_bin_table=size_bin_table,
        example_row_table=example_row_table,
        country_table=build_country_table(clean_countries),
        sample_n_polygons=sample_n_polygons,
    )

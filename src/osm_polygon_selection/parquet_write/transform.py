"""Table transformation helpers for the parquet_write pipeline.

Two complementary paths:
- ``build_columns`` converts a Python list of dicts to per-column
  lists (the legacy per-row writer).
- ``reshape_parsed_table`` adds metadata, splits centroid, renames
  geometry on a pyarrow Table (the fast pyarrow.json path).
"""

from __future__ import annotations

from typing import Sequence

import pyarrow as pa

from osm_polygon_selection.schema_defs import build_schema


def build_columns(
    rows: list[dict],
    country: str,
    extract_status: str,
    pbf_date: str,
    geometry_encoding: str,
) -> dict[str, list]:
    """Convert a chunk of source rows into per-column lists."""
    n = len(rows)
    try:
        osm_ids = [int(r["osm_id"]) for r in rows]
    except (KeyError, TypeError, ValueError):
        osm_ids = [int(r.get("osm_id", 0)) for r in rows]
    osm_types = [str(r.get("osm_type", "")) for r in rows]
    areas = [float(r.get("area_km2", 0.0)) for r in rows]
    matched_tags = [str(r.get("matched_tag") or "") for r in rows]
    continents = [str(r.get("continent", "unknown")) for r in rows]
    size_bins = [str(r.get("size_bin", "small")) for r in rows]
    tags_list = [list(r.get("tags") or []) for r in rows]
    centroids = [(r.get("centroid") or [None, None]) for r in rows]
    centroid_lons = [
        float(c[0]) if c and c[0] is not None else 0.0 for c in centroids
    ]
    centroid_lats = [
        float(c[1]) if c and len(c) > 1 and c[1] is not None else 0.0
        for c in centroids
    ]
    cols: dict[str, list] = {
        "osm_id": osm_ids,
        "osm_type": osm_types,
        "centroid_lon": centroid_lons,
        "centroid_lat": centroid_lats,
        "area_km2": areas,
        "tags": tags_list,
        "matched_tag": matched_tags,
        "continent": continents,
        "size_bin": size_bins,
        "country": [country] * n,
        "extract_status": [extract_status] * n,
        "pbf_date": [pbf_date] * n,
    }
    if geometry_encoding == "wkt":
        cols["geometry_wkt"] = [r.get("geometry") for r in rows]
    elif geometry_encoding == "wkb":
        from osm_polygon_selection.schema_defs import encode_geometry
        cols["geometry_wkb"] = [
            encode_geometry(r.get("geometry"), geometry_encoding) for r in rows
        ]
    return cols


def split_centroid(centroid_col: pa.Array, idx: int) -> pa.Array:
    """Extract a scalar column (lon or lat) from a list<float> column."""
    import pyarrow.compute as pc
    from osm_polygon_selection.pyarrow_compat import list_element
    return pc.cast(list_element(centroid_col, idx), pa.float64())


def reshape_parsed_table(
    table: pa.Table,
    country: str,
    extract_status: str,
    pbf_date: str,
    geometry_encoding: str,
) -> pa.Table:
    """Add metadata, split centroid, rename geometry on a parsed JSONL table."""
    cols: dict[str, pa.Array] = {}
    seen: dict[str, int] = {}
    for i, name in enumerate(table.column_names):
        arr = table.column(i)
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        cols[name] = arr

    n = table.num_rows
    out: dict[str, pa.Array] = {}
    for src, dst in (
        ("osm_id", "osm_id"),
        ("osm_type", "osm_type"),
        ("area_km2", "area_km2"),
        ("matched_tag", "matched_tag"),
        ("continent", "continent"),
        ("size_bin", "size_bin"),
        ("tags", "tags"),
    ):
        if dst in cols:
            out[dst] = cols[dst]

    centroid = cols.get("centroid")
    if centroid is not None:
        out["centroid_lon"] = split_centroid(centroid, idx=0)
        out["centroid_lat"] = split_centroid(centroid, idx=1)

    out["country"] = pa.array([country] * n, type=pa.string())
    out["extract_status"] = pa.array([extract_status] * n, type=pa.string())
    out["pbf_date"] = pa.array([pbf_date] * n, type=pa.string())

    geom = cols.get("geometry")
    if geom is not None:
        if geometry_encoding == "wkt":
            out["geometry_wkt"] = geom
        else:
            from osm_polygon_selection.schema_defs import encode_geometry
            py_values = geom.to_pylist()
            wkb_values = [encode_geometry(v, geometry_encoding) for v in py_values]
            out["geometry_wkb"] = pa.array(wkb_values, type=pa.binary())

    target_schema = build_schema(geometry_encoding=geometry_encoding)
    for name, field in zip(
        [f.name for f in target_schema],
        target_schema,
    ):
        if name not in out:
            out[name] = pa.array([None] * n, type=field.type)

    ordered = [out[f.name] for f in target_schema]
    return pa.table(ordered, schema=target_schema)

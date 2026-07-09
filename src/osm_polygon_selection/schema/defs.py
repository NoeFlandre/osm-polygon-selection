"""PyArrow schema definitions + geometry encoding helpers (canonical).

See :mod:`osm_polygon_selection.schema` for the package overview.
"""

from __future__ import annotations

import pyarrow as pa

GEOMETRY_ENCODING_DEFAULT = "wkt"

# Base columns (always present).
_BASE_COLUMNS: list[tuple[str, pa.DataType]] = [
    ("osm_id", pa.int64()),
    ("osm_type", pa.string()),
    ("centroid_lon", pa.float64()),
    ("centroid_lat", pa.float64()),
    ("area_km2", pa.float64()),
    ("tags", pa.list_(pa.string())),
    ("matched_tag", pa.string()),
    ("continent", pa.string()),
    ("size_bin", pa.string()),
    ("country", pa.string()),
    ("extract_status", pa.string()),
    ("pbf_date", pa.string()),
]

# Optional columns (added on demand).
_SPLIT_COLUMN: tuple[str, pa.DataType] = ("split", pa.string())


def build_schema(
    geometry_encoding: str = GEOMETRY_ENCODING_DEFAULT,
    include_split: bool = False,
) -> pa.Schema:
    """Return the pyarrow schema for the dataset parquet files.

    Args:
        geometry_encoding: one of ``"wkt"``, ``"wkb"``, ``"none"``.
            ``"wkt"`` (default) keeps the geometry as WKT text.
            ``"wkb"`` serializes to WKB binary (~50% smaller).
            ``"none"`` drops the geometry column entirely.
        include_split: if True, append a ``split`` column
            (``train`` / ``val`` / ``test``). Only included after
            ``make_split.py`` has run.
    """
    fields = list(_BASE_COLUMNS)
    if geometry_encoding == "wkt":
        fields.append(("geometry_wkt", pa.string()))
    elif geometry_encoding == "wkb":
        fields.append(("geometry_wkb", pa.binary()))
    elif geometry_encoding == "none":
        pass  # no geometry column
    else:
        raise ValueError(
            f"geometry_encoding must be wkt, wkb, or none; got {geometry_encoding!r}"
        )
    if include_split:
        fields.append(_SPLIT_COLUMN)
    return pa.schema(fields)


def get_column_order(
    geometry_encoding: str = GEOMETRY_ENCODING_DEFAULT,
    include_split: bool = False,
) -> list[str]:
    """Return the column names in their canonical order.

    Mirrors ``build_schema`` — useful for writing manifests and
    for scripts that build rows without using the schema object.
    """
    cols = [name for name, _ in _BASE_COLUMNS]
    if geometry_encoding == "wkt":
        cols.append("geometry_wkt")
    elif geometry_encoding == "wkb":
        cols.append("geometry_wkb")
    # "none" -> no geometry column
    if include_split:
        cols.append("split")
    return cols


def encode_geometry(
    wkt: str | None,
    encoding: str = GEOMETRY_ENCODING_DEFAULT,
) -> bytes | str | None:
    """Encode a WKT geometry string to the requested format.

    Returns ``None`` if input is empty or encoding is "none".
    """
    if not wkt or encoding == "none":
        return None
    if encoding == "wkt":
        return wkt
    # WKB: parse the WKT and serialize to binary.
    import shapely.wkt as _shapely_wkt

    return _shapely_wkt.loads(wkt).wkb


# ---------------------------------------------------------------------------
# Documentation metadata (used by README writers)
# ---------------------------------------------------------------------------

COLUMN_TYPES: dict[str, str] = {
    "osm_id": "int64",
    "osm_type": "string",
    "centroid_lon": "float64",
    "centroid_lat": "float64",
    "area_km2": "float64",
    "tags": "list(string)",
    "matched_tag": "string",
    "continent": "string",
    "size_bin": "string",
    "country": "string",
    "extract_status": "string",
    "pbf_date": "string",
    "geometry_wkt": "string",
    "geometry_wkb": "binary",
    "split": "string",
}

COLUMN_DESCRIPTIONS: dict[str, str] = {
    "osm_id": "OSM object id (int64).",
    "osm_type": 'OSM object type, "way" or "relation" (string).',
    "centroid_lon": "polygon centroid longitude (WGS84, float64).",
    "centroid_lat": "polygon centroid latitude (WGS84, float64).",
    "area_km2": "polygon area in km² (Web Mercator, float64).",
    "tags": "OSM `key=value` tags (list of strings).",
    "matched_tag": (
        "the first tag in `tags` that hit the whitelist "
        "(string, the reason the polygon survived)."
    ),
    "continent": "Natural Earth admin0 lookup of the centroid (string).",
    "size_bin": '"small" (0.1-1), "medium" (1-10), or "large" (10-100) km² (string).',
    "country": "ISO-style country name (string).",
    "extract_status": (
        '"clean" (extract ran to completion) or "killed" (extract was interrupted) (string).'
    ),
    "pbf_date": "date of the source PBF file (string, from mtime).",
    "geometry_wkt": (
        "polygon geometry as WKT (WGS84, string). "
        "Parse with `shapely.wkt.loads(row.geometry_wkt)`."
    ),
    "geometry_wkb": (
        "polygon geometry as WKB (WGS84, binary). "
        "Parse with `shapely.wkb.loads(row.geometry_wkb)`."
    ),
    "split": (
        '"train", "val", or "test" (stratified by country, '
        "see Train/val/test split section below)."
    ),
}

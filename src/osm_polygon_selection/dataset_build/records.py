"""Record-level data transforms used by ``build_dataset.py``.

These functions are pure: they take data + parameters and return
records. They do not touch the filesystem or read module-level state.

- ``row_to_record``: convert a 03_classified.jsonl row + metadata into
  a dataset record (the row that ends up in the per-country parquet).
- ``pbf_date_for``: read the PBF date from the raw mtime.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

__all__ = ["row_to_record", "pbf_date_for"]


def row_to_record(
    row: dict,
    country: str,
    status: str,
    pbf_date: str,
    geometry_encoding: str,
    whitelist: set[str],
) -> dict[str, Any] | None:
    """Convert one JSONL row + metadata into a dataset record.

    Parameters
    ----------
    row:
        The row from ``03_classified.jsonl`` (dict with osm_id,
        osm_type, centroid, area_km2, tags, continent, size_bin,
        geometry, optional matched_tag).
    country:
        The country/region name (e.g. ``"france"``).
    status:
        ``"clean"`` or ``"killed"`` (from the package's
        ``extract_status`` helper).
    pbf_date:
        ISO date string for the source PBF (from ``pbf_date_for``).
    geometry_encoding:
        One of ``"wkt"``, ``"wkb"``, ``"none"``. Controls whether
        and how the geometry column is emitted.
    whitelist:
        The OSM tag whitelist. Used to backfill ``matched_tag`` for
        rows that pre-date the column.

    Returns
    -------
    dict or None
        The record dict, or ``None`` if the row is malformed.
    """
    try:
        centroid = row.get("centroid", [None, None])
        rec: dict[str, Any] = {
            "osm_id": int(row["osm_id"]),
            "osm_type": str(row.get("osm_type", "")),
            "centroid_lon": float(centroid[0]) if centroid and len(centroid) > 0 else None,
            "centroid_lat": float(centroid[1]) if centroid and len(centroid) > 1 else None,
            "area_km2": float(row.get("area_km2", 0.0)),
            "tags": list(row.get("tags", [])),
            "matched_tag": _compute_matched_tag(row, whitelist),
            "continent": str(row.get("continent", "unknown")),
            "size_bin": str(row.get("size_bin", "small")),
            "country": country,
            "extract_status": status,
            "pbf_date": pbf_date,
        }
        geom = _encode_geometry(row.get("geometry"), geometry_encoding)
        if geometry_encoding == "wkt":
            rec["geometry_wkt"] = geom
        elif geometry_encoding == "wkb":
            rec["geometry_wkb"] = geom
        return rec
    except (KeyError, TypeError, ValueError):
        return None


def pbf_date_for(country: str, raw_root: Path) -> str:
    """Return the date of the source PBF as ``YYYY-MM-DD``.

    Returns ``"unknown"`` if the PBF is not present.
    """
    pbf = Path(raw_root) / f"{country}-latest.osm.pbf"
    if not pbf.exists():
        return "unknown"
    mtime = pbf.stat().st_mtime
    return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")


# --- private helpers -------------------------------------------------------


def _compute_matched_tag(row: dict, whitelist: set[str]) -> str:
    """Return the row's existing ``matched_tag`` or the first whitelist hit.

    Older ``03_classified.jsonl`` files (pre-``matched_tag``) don't
    have this field, so we backfill from ``row.tags`` against the
    whitelist.
    """
    existing = row.get("matched_tag")
    if existing:
        return str(existing)
    for t in row.get("tags", []):
        if t in whitelist:
            return str(t)
    return ""


def _encode_geometry(
    wkt: str | None, encoding: str
) -> bytes | str | None:
    """Encode a WKT geometry to the requested format.

    Returns ``None`` if input is empty or encoding is ``"none"``.
    """
    if not wkt or encoding == "none":
        return None
    if encoding == "wkt":
        return wkt
    # WKB
    import shapely.wkt as _shapely_wkt

    return _shapely_wkt.loads(wkt).wkb

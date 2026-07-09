"""Shared helpers for streaming-writer tests."""

from __future__ import annotations

import json
from pathlib import Path

import pyarrow.parquet as pq


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def _row(
    osm_id: int,
    lon: float = 10.0,
    lat: float = 50.0,
    area: float = 1.0,
    tags: list[str] | None = None,
    matched_tag: str = "",
    continent: str = "Europe",
    size_bin: str = "small",
    geometry: str = "POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))",
) -> dict:
    return {
        "osm_id": osm_id,
        "osm_type": "way",
        "centroid": [lon, lat],
        "area_km2": area,
        "tags": tags or ["natural=water"],
        "matched_tag": matched_tag,
        "continent": continent,
        "size_bin": size_bin,
        "geometry": geometry,
    }


def _read_parquet(path: Path) -> pq.Table:
    return pq.read_table(path)


def _row_group_count(path: Path) -> int:
    return pq.ParquetFile(path).num_row_groups


__all__ = [
    "_read_parquet",
    "_row",
    "_row_group_count",
    "_write_jsonl",
]

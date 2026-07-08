"""Streaming JSONL -> parquet writer (facade).

Backwards-compatible re-export of ``write_jsonl_to_parquet``. The
heavy lifting lives in :mod:`osm_polygon_selection.parquet_write`:

- :mod:`.atomic` — atomic write helpers
- :mod:`.jsonl` — Python-JSONL per-row legacy writer
- :mod:`.transform` — table reshape
- :mod:`.matched_tags` — matched_tag backfill
"""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.json as paj
import pyarrow.parquet as pq

from osm_polygon_selection.parquet_write.atomic import atomic_write_empty_parquet
from osm_polygon_selection.parquet_write.jsonl import (
    write_jsonl_to_parquet_python_json,
)
from osm_polygon_selection.parquet_write.matched_tags import (
    maybe_backfill_matched_tag_pa,
)
from osm_polygon_selection.parquet_write.transform import reshape_parsed_table
from osm_polygon_selection.schema_defs import build_schema

CHUNK_SIZE = 50_000

# Re-export the private Python-JSON path for backwards-compat tests.
_write_jsonl_to_parquet_python_json = write_jsonl_to_parquet_python_json

__all__ = [
    "CHUNK_SIZE",
    "_write_jsonl_to_parquet_python_json",
    "write_jsonl_to_parquet",
]


def write_jsonl_to_parquet(
    jsonl_path: Path,
    parquet_path: Path,
    country: str,
    extract_status: str,
    pbf_date: str,
    geometry_encoding: str = "wkt",
    whitelist_path: Path | None = None,
    chunk_size: int = CHUNK_SIZE,
    compression: str = "zstd",
    compression_level: int = 1,
) -> int:
    """Stream ``jsonl_path`` to ``parquet_path`` via pyarrow C-level parser.

    Returns the number of rows written.
    """
    if not jsonl_path.is_file():
        raise FileNotFoundError(f"jsonl not found: {jsonl_path}")

    # Empty JSONL: produce a header-only parquet in our schema.
    if jsonl_path.stat().st_size == 0:
        atomic_write_empty_parquet(
            parquet_path,
            build_schema(geometry_encoding=geometry_encoding),
        )
        return 0

    # 1. Parse the whole JSONL with the C-level pyarrow parser.
    #    Fall back to the per-row Python path on malformed lines.
    try:
        raw_table = paj.read_json(jsonl_path)
    except pa.lib.ArrowInvalid:
        return write_jsonl_to_parquet_python_json(
            jsonl_path=jsonl_path,
            parquet_path=parquet_path,
            country=country,
            extract_status=extract_status,
            pbf_date=pbf_date,
            geometry_encoding=geometry_encoding,
            whitelist_path=whitelist_path,
            chunk_size=chunk_size,
        )

    # 2. Reshape: metadata, centroid split, geometry rename.
    transformed = reshape_parsed_table(
        raw_table,
        country=country,
        extract_status=extract_status,
        pbf_date=pbf_date,
        geometry_encoding=geometry_encoding,
    )

    # 3. Backfill matched_tag if needed.
    if whitelist_path is not None:
        transformed = maybe_backfill_matched_tag_pa(transformed, whitelist_path)

    # 4. Atomic write.
    from osm_polygon_selection.parquet_write.atomic import atomic_write_parquet

    def _write(tmp: Path) -> None:
        kwargs: dict = {
            "compression": compression,
            "row_group_size": chunk_size,
            "write_page_index": True,
        }
        if compression == "zstd" and compression_level is not None:
            kwargs["compression_level"] = compression_level
        pq.write_table(transformed, tmp, **kwargs)

    atomic_write_parquet(parquet_path, _write, prefix=".build_")
    return transformed.num_rows

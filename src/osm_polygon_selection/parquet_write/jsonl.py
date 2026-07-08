"""JSONL parsing + per-row Python writer for the parquet_write pipeline.

This is the LEGACY path: per-row ``json.loads`` + per-chunk
``pa.record_batch``. Kept for benchmarking and for the
``_write_jsonl_to_parquet_python_json`` fallback when the
pyarrow C-level JSON parser rejects a malformed line.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from osm_polygon_selection.parquet_write.atomic import atomic_write_parquet
from osm_polygon_selection.parquet_write.matched_tags import maybe_backfill_matched_tag
from osm_polygon_selection.parquet_write.transform import build_columns
from osm_polygon_selection.schema_defs import build_schema


def write_jsonl_to_parquet_python_json(
    jsonl_path: Path,
    parquet_path: Path,
    country: str,
    extract_status: str,
    pbf_date: str,
    geometry_encoding: str = "wkt",
    whitelist_path: Path | None = None,
    chunk_size: int = 50_000,
) -> int:
    """Per-row Python json.loads path. Skips malformed JSON lines."""
    if not jsonl_path.is_file():
        raise FileNotFoundError(f"jsonl not found: {jsonl_path}")
    schema = build_schema(geometry_encoding=geometry_encoding)
    n_total = 0

    def _write(tmp: Path) -> None:
        nonlocal n_total
        writer = pq.ParquetWriter(
            tmp, schema, compression="zstd",
            compression_level=1, write_page_index=True,
        )
        try:
            chunk: list[dict] = []
            with jsonl_path.open() as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError as e:
                        print(f"  skipping malformed JSON: {e}", file=sys.stderr)
                        continue
                    chunk.append(row)
                    if len(chunk) >= chunk_size:
                        n_total += _write_chunk_pj(
                            writer, chunk, country, extract_status,
                            pbf_date, geometry_encoding, whitelist_path,
                        )
                        chunk = []
                if chunk:
                    n_total += _write_chunk_pj(
                        writer, chunk, country, extract_status,
                        pbf_date, geometry_encoding, whitelist_path,
                    )
        finally:
            writer.close()

    atomic_write_parquet(parquet_path, _write, prefix=".build_py_")
    return n_total


def _write_chunk_pj(
    writer: pq.ParquetWriter,
    chunk: list[dict],
    country: str,
    extract_status: str,
    pbf_date: str,
    geometry_encoding: str,
    whitelist_path: Path | None,
) -> int:
    cols = build_columns(chunk, country, extract_status, pbf_date, geometry_encoding)
    maybe_backfill_matched_tag(cols, whitelist_path)
    batch = pa.record_batch(
        [pa.array(cols[name], type=field.type) for name, field in zip(
            [f.name for f in writer.schema],
            writer.schema,
        )],
        schema=writer.schema,
    )
    writer.write_batch(batch)
    return len(chunk)

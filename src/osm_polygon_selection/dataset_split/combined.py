"""Streaming combined-parquet writer.

Walks per-country parquets in manifest order, computes the
deterministic split for each country, and writes a single
combined parquet with a trailing ``split`` column. Per-country
parquets are NEVER modified.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from osm_polygon_selection.dataset_split.assignment import assign_split_for_country
from osm_polygon_selection.dataset_split.config import (
    COMPRESSION,
    COMPRESSION_LEVEL,
    ROW_GROUP_SIZE,
    SPLIT_TYPE,
)
from osm_polygon_selection.dataset_split.manifest import read_dataset_manifest


def _country_total_rows(parquet_path: Path) -> int:
    src = pq.ParquetFile(parquet_path)
    return sum(
        src.metadata.row_group(i).num_rows for i in range(src.num_row_groups)
    )


def _append_split_column(batch: pa.RecordBatch, splits: pa.Array) -> pa.RecordBatch:
    if "split" in batch.schema.names:
        idx = batch.schema.get_field_index("split")
        batch = batch.remove_column(idx)
    return batch.append_column("split", splits)


def write_combined_streaming(
    root: Path,
    *,
    seed: int,
    ratios: dict[str, float],
    manifest: dict | None = None,
) -> int:
    """Rebuild ``combined/all_world.parquet`` with a trailing split column.

    Concatenates per-country parquets WITHOUT materializing them all
    in memory: walks each parquet's row groups in order and writes
    them one at a time via ``ParquetWriter.write_batch``.

    The combined parquet has the same columns as the per-country
    parquets PLUS a trailing ``split`` column. Each row group
    receives its slice of the deterministic split assignment
    (``assign_split_for_country(country_index, seed, ratios)``) so
    per-row split membership is consistent with
    ``split_manifest.json``.

    Per-country parquets are NEVER rewritten here. The split column
    is only persisted in the combined file.

    Returns the number of rows written.
    """
    if manifest is None:
        manifest = read_dataset_manifest(root)

    base_schema: pa.Schema | None = None
    for c_info in manifest["countries"]:
        c = c_info["country"]
        pq_path = root / "per_country" / c / f"{c}.parquet"
        if pq_path.is_file():
            base_schema = pq.read_schema(pq_path)
            break
    if base_schema is None:
        raise RuntimeError("no per-country parquets to combine")

    if "split" in base_schema.names:
        base_schema = pa.schema([f for f in base_schema if f.name != "split"])
    combined_schema = base_schema.append(pa.field("split", SPLIT_TYPE))

    out = root / "combined" / "all_world.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=".combined_", suffix=".parquet", dir=str(out.parent),
    )
    os.close(fd)
    total_rows = 0
    try:
        writer = pq.ParquetWriter(
            tmp_path,
            combined_schema,
            compression=COMPRESSION,
            compression_level=COMPRESSION_LEVEL,
            write_page_index=True,
        )
        try:
            for idx, c_info in enumerate(manifest["countries"]):
                c = c_info["country"]
                pq_path = root / "per_country" / c / f"{c}.parquet"
                if not pq_path.is_file():
                    continue
                n_rows = _country_total_rows(pq_path)
                splits = assign_split_for_country(
                    n_rows, idx, seed, ratios,
                )
                src = pq.ParquetFile(pq_path)
                row_offset = 0
                for rg_idx in range(src.num_row_groups):
                    tbl = src.read_row_group(rg_idx)
                    batch = pa.RecordBatch.from_arrays(
                        [tbl.column(i).combine_chunks() for i in range(tbl.num_columns)],
                        schema=tbl.schema,
                    )
                    rg_rows = batch.num_rows
                    rg_splits = pa.array(
                        splits[row_offset:row_offset + rg_rows].tolist(),
                        type=SPLIT_TYPE,
                    )
                    batch = _append_split_column(batch, rg_splits)
                    pos = 0
                    while pos < rg_rows:
                        end = min(pos + ROW_GROUP_SIZE, rg_rows)
                        writer.write_batch(batch.slice(pos, end - pos))
                        pos = end
                    row_offset += rg_rows
                    total_rows += rg_rows
        finally:
            writer.close()
        os.replace(tmp_path, out)
    except Exception:
        if Path(tmp_path).is_file():
            os.unlink(tmp_path)
        raise
    return total_rows


__all__ = ["write_combined_streaming"]

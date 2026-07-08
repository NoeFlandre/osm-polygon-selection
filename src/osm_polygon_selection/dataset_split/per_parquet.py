"""Per-parquet append helper (used only by legacy test path).

The make_split optimization (commit ``1edc041``) stopped rewriting
per-country parquets. The streaming helper for appending a split
column to a single parquet is preserved here for backwards-compat
tests (``tests/splitting/test_make_split.py``) and for any future
single-file rewrite.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from osm_polygon_selection.dataset_split.config import (
    COMPRESSION,
    COMPRESSION_LEVEL,
    ROW_GROUP_SIZE,
    SPLIT_TYPE,
)


def _append_split(batch: pa.RecordBatch, splits: pa.Array) -> pa.RecordBatch:
    if "split" in batch.schema.names:
        idx = batch.schema.get_field_index("split")
        batch = batch.remove_column(idx)
    return batch.append_column("split", splits)


def add_split_column_streaming(parquet_path: Path, splits: np.ndarray) -> None:
    """Append a ``split`` column to a single parquet, in place.

    Reads the source parquet one row group at a time, appends the
    pre-computed split column to each row group's batch, and writes
    it back via ``ParquetWriter.write_batch``. Memory cost is
    O(ROW_GROUP_SIZE) per row group instead of O(table size).
    """
    src = pq.ParquetFile(parquet_path)
    base_schema = src.schema_arrow
    has_split = "split" in base_schema.names
    if has_split:
        new_fields = [f for f in base_schema if f.name != "split"]
        new_schema = pa.schema(new_fields + [pa.field("split", SPLIT_TYPE)])
    else:
        new_schema = base_schema.append(pa.field("split", SPLIT_TYPE))

    tmp_dir = parquet_path.parent
    fd, tmp_path = tempfile.mkstemp(
        prefix=".split_", suffix=".parquet", dir=str(tmp_dir),
    )
    os.close(fd)
    try:
        writer = pq.ParquetWriter(
            tmp_path,
            new_schema,
            compression=COMPRESSION,
            compression_level=COMPRESSION_LEVEL,
            write_page_index=True,
        )
        try:
            offset = 0
            for rg_idx in range(src.num_row_groups):
                tbl = src.read_row_group(rg_idx)
                batch = pa.RecordBatch.from_arrays(
                    [tbl.column(i).combine_chunks() for i in range(tbl.num_columns)],
                    schema=tbl.schema,
                )
                rg_rows = batch.num_rows
                rg_splits = pa.array(
                    splits[offset:offset + rg_rows].tolist(), type=SPLIT_TYPE,
                )
                batch = _append_split(batch, rg_splits)
                pos = 0
                while pos < rg_rows:
                    end = min(pos + ROW_GROUP_SIZE, rg_rows)
                    writer.write_batch(batch.slice(pos, end - pos))
                    pos = end
                offset += rg_rows
        finally:
            writer.close()
        os.replace(tmp_path, parquet_path)
    except Exception:
        if Path(tmp_path).is_file():
            os.unlink(tmp_path)
        raise


__all__ = ["add_split_column_streaming"]

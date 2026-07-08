"""Atomic write helpers for the parquet_write pipeline.

A "write atomic" operation writes to a temporary file in the
target directory and then ``os.replace``'s it onto the final
path. This means a partial write never leaves a half-baked
parquet at the destination.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Callable, TypeVar

T = TypeVar("T")


def atomic_write_parquet(
    out_path: Path,
    write_fn: Callable[[Path], T],
    *,
    prefix: str = ".build_",
) -> T:
    """Run ``write_fn(tmp_path)`` then ``os.replace`` the result.

    On exception the temp file is removed before re-raising.
    Returns whatever ``write_fn`` returns.
    """
    out_dir = out_path.parent
    fd, tmp_path = tempfile.mkstemp(
        prefix=prefix, suffix=".parquet", dir=str(out_dir),
    )
    os.close(fd)
    try:
        result = write_fn(Path(tmp_path))
    except Exception:
        if Path(tmp_path).is_file():
            os.unlink(tmp_path)
        raise
    os.replace(tmp_path, out_path)
    return result


def atomic_write_empty_parquet(
    out_path: Path,
    schema,
    *,
    compression: str = "zstd",
    compression_level: int | None = 1,
    row_group_size: int = 50_000,
    write_page_index: bool = True,
    prefix: str = ".build_",
) -> None:
    """Write a header-only empty parquet at ``out_path`` (atomic)."""
    import pyarrow.parquet as pq

    def _write(tmp: Path) -> None:
        empty = schema.empty_table()
        kwargs: dict = {
            "compression": compression,
            "row_group_size": row_group_size,
            "write_page_index": write_page_index,
        }
        if compression == "zstd" and compression_level is not None:
            kwargs["compression_level"] = compression_level
        pq.write_table(empty, tmp, **kwargs)

    atomic_write_parquet(out_path, _write, prefix=prefix)

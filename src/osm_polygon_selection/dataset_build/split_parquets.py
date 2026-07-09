"""Stream-filter a combined parquet into one parquet per split.

Reads a source parquet that contains a ``split`` column
(``"train"`` / ``"val"`` / ``"test"``) and writes one parquet per
split under ``out_dir``. The output schema drops the uniform
``split`` column.

Implementation note: we open one :class:`pyarrow.parquet.ParquetWriter`
per split and append each filtered row group to the right writer.
This avoids holding the full filtered table in memory, which OOMs
for the 14M-row worldwide dataset.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pyarrow as pa
import pyarrow.parquet as pq

from osm_polygon_selection.io.pyarrow_compat import equal

__all__ = ["write_split_parquets"]

SPLITS: Final[tuple[str, ...]] = ("train", "val", "test")


def write_split_parquets(source: Path, out_dir: Path) -> dict[str, int]:
    """Write one parquet per split from a combined parquet.

    Parameters
    ----------
    source:
        Path to a parquet containing a ``split`` column.
    out_dir:
        Directory to write ``train.parquet`` / ``val.parquet`` /
        ``test.parquet`` into. Created if it does not exist.

    Returns
    -------
    dict[str, int]
        Row counts per split.

    Raises
    ------
    FileNotFoundError
        If ``source`` does not exist.
    """
    source_path = Path(source)
    if not source_path.is_file():
        raise FileNotFoundError(f"missing source: {source_path}")

    out_dir_path = Path(out_dir)
    out_dir_path.mkdir(parents=True, exist_ok=True)

    pf = pq.ParquetFile(source_path)
    full_schema = pf.schema_arrow
    field_names = [n for n in full_schema.names if n != "split"]
    writer_schema = pa.schema([full_schema.field(n) for n in field_names])

    writers: dict[str, pq.ParquetWriter] = {
        split: pq.ParquetWriter(
            out_dir_path / f"{split}.parquet",
            writer_schema,
            compression="zstd",
            compression_level=1,
            write_page_index=True,
        )
        for split in SPLITS
    }
    counts: dict[str, int] = {split: 0 for split in SPLITS}
    try:
        for rg_idx in range(pf.num_row_groups):
            rg = pf.read_row_group(rg_idx)
            for split in SPLITS:
                sub = rg.filter(equal(rg["split"], split))
                n = sub.num_rows
                if n > 0:
                    writers[split].write_table(sub.drop(["split"]))
                    counts[split] += n
    finally:
        # Always close every writer, even if processing failed mid-loop.
        # ParquetWriter needs an explicit close() to flush the footer
        # and release the file handle; otherwise the partial output
        # file is left on disk and unreadable.
        for w in writers.values():
            w.close()

    return counts

"""Stream-filter and write a single combined parquet from per-country files.

The combined parquet (``combined/all_world.parquet``) is one parquet
that concatenates every per-country parquet into a single row group
chain. Building it requires holding ~14M rows; in-memory
``pa.concat_tables`` OOMs at this size. We stream by:

1. Reading the schema from the first non-empty per-country file.
2. Opening a single ``ParquetWriter`` on the target path.
3. Reading each per-country file and writing it to the writer.
4. Closing the writer in a ``finally`` so partial writes are not
   left in an unreadable state.

This module is the package-owned version of the inline code that
previously lived inside ``scripts/build_dataset.py::main``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping

import pyarrow.parquet as pq

__all__ = ["combine_per_country_parquets"]


def combine_per_country_parquets(
    out_dir: Path,
    countries: Iterable[Mapping],
    output_path: Path | None = None,
) -> int:
    """Stream-append every per-country parquet into one combined file.

    Parameters
    ----------
    out_dir:
        Directory containing ``<country>.parquet`` files (one per country).
    countries:
        Iterable of manifest rows. Each row must have a ``country``
        string and an ``n_polygons`` int. Rows with ``n_polygons == 0``
        are skipped silently.
    output_path:
        Where to write the combined parquet. Default: ``out_dir / "all_world.parquet"``.

    Returns
    -------
    int
        Total number of rows written.

    Raises
    ------
    FileNotFoundError
        If no per-country parquet can be found to derive a schema from.
    """
    out_dir_path = Path(out_dir)
    countries_list = list(countries)

    # Find the first country that has a parquet file (we need its schema).
    schema_source: Path | None = None
    for c in countries_list:
        if int(c.get("n_polygons", 0)) > 0:
            candidate = out_dir_path / f"{c['country']}.parquet"
            if candidate.is_file():
                schema_source = candidate
                break

    if schema_source is None:
        raise FileNotFoundError(
            f"no per-country parquet files found under {out_dir_path}"
        )

    schema = pq.read_schema(schema_source)
    out_path = Path(output_path) if output_path else out_dir_path / "all_world.parquet"

    writer: pq.ParquetWriter | None = None
    total_rows = 0
    try:
        writer = pq.ParquetWriter(
            out_path,
            schema,
            compression="zstd",
            compression_level=1,
            write_page_index=True,
        )
        for c in countries_list:
            if int(c.get("n_polygons", 0)) == 0:
                continue
            table_path = out_dir_path / f"{c['country']}.parquet"
            if not table_path.is_file():
                continue
            table = pq.read_table(table_path)
            writer.write_table(table)
            total_rows += table.num_rows
    finally:
        if writer is not None:
            # Always close — even on exception — so the partial
            # parquet is not left in an unreadable state.
            writer.close()

    return total_rows

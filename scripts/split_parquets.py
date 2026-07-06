"""Write per-split parquet files so the HuggingFace viewer exposes them.

The HF dataset viewer detects "splits" by the directory structure
of parquet files. With a single ``combined/all_world.parquet`` that
has a ``split`` column, the viewer only shows one config (default).

By writing ``splits/train-*.parquet``, ``splits/val-*.parquet``,
``splits/test-*.parquet`` (chunks of the full file filtered to one
split each), the viewer surfaces all three as separate tabs.

Output: writes the chunked split files under ``dataset/splits/``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

DEFAULT_ROOT = Path("/Volumes/Seagate M3/osm-polygon-selection/dataset")
SOURCE = DEFAULT_ROOT / "combined" / "all_world.parquet"
SPLITS_DIR = DEFAULT_ROOT / "splits"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--out", type=Path, default=SPLITS_DIR)
    args = parser.parse_args()

    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    if not args.source.is_file():
        print(f"missing source: {args.source}")
        return 1

    print(f"reading {args.source}", flush=True)
    pf = pq.ParquetFile(args.source)
    full_schema = pf.schema_arrow
    # Writer schema drops the "split" column (uniform within each
    # per-split output file).
    field_names = [n for n in full_schema.names if n != "split"]
    writer_schema = pa.schema(
        [full_schema.field(n) for n in field_names]
    )
    print(f"  writer schema: {writer_schema.names}", flush=True)

    # Open one writer per split; append each filtered row group
    # directly to the right writer. This avoids holding 14M rows
    # in memory (peak ~4 GB) — the previous "concat_tables then
    # write" approach OOM'd at row group 400/467.
    writers: dict[str, pq.ParquetWriter] = {}
    for split in ("train", "val", "test"):
        writers[split] = pq.ParquetWriter(
            out_dir / f"{split}.parquet",
            writer_schema,
            compression="zstd",
            compression_level=1,
            write_page_index=True,
        )
    counts: dict[str, int] = {"train": 0, "val": 0, "test": 0}
    for rg_idx in range(pf.num_row_groups):
        rg = pf.read_row_group(rg_idx)
        for split in ("train", "val", "test"):
            mask = pc.equal(rg["split"], split)
            sub = rg.filter(mask)
            n = sub.num_rows
            if n > 0:
                # Drop the now-uniform "split" column.
                writers[split].write_table(sub.drop(["split"]))
                counts[split] += n
        if rg_idx % 20 == 0:
            print(
                f"  row group {rg_idx}/{pf.num_row_groups}: "
                f"train={counts['train']:,} val={counts['val']:,} "
                f"test={counts['test']:,}",
                flush=True,
            )
    for w in writers.values():
        w.close()

    for split in ("train", "val", "test"):
        out = out_dir / f"{split}.parquet"
        size_mb = out.stat().st_size / 1_048_576
        print(f"  {split}: {counts[split]:,} rows -> {out.name} ({size_mb:.1f} MB)", flush=True)

    return 0

    counts = {}
    for split in ("train", "val", "test"):
        mask = pc.equal(table["split"], split)
        sub = table.filter(mask)
        n = sub.num_rows
        counts[split] = n
        out = out_dir / f"{split}.parquet"
        # Drop the "split" column from the chunked files since
        # all rows in train.parquet are train, etc.
        sub = sub.drop(["split"])
        # Stream the rows in row-group-sized chunks so peak
        # memory stays bounded for the 14M-row filter.
        pq.write_table(
            sub,
            out,
            compression="zstd",
            compression_level=1,
            row_group_size=50_000,
            write_page_index=True,
        )
        size_mb = out.stat().st_size / 1_048_576
        print(f"  {split}: {n:,} rows -> {out.name} ({size_mb:.1f} MB)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Thin CLI around `osm_polygon_selection.dataset_build.split_parquets`.

Writes `splits/{train,val,test}.parquet` so the HuggingFace dataset
viewer exposes each split as a separate tab. The actual stream-filter
logic lives in the package; this script is just argument parsing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from osm_polygon_selection.dataset_build.split_parquets import write_split_parquets
from osm_polygon_selection.runtime_config import RuntimeConfig

_DEFAULT_CONFIG = RuntimeConfig.from_env()
DEFAULT_ROOT = _DEFAULT_CONFIG.dataset_root
DEFAULT_SOURCE = DEFAULT_ROOT / "combined" / "all_world.parquet"
DEFAULT_OUT = DEFAULT_ROOT / "splits"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    print(f"reading {args.source}", flush=True)
    counts = write_split_parquets(args.source, args.out)

    for split in ("train", "val", "test"):
        out = args.out / f"{split}.parquet"
        size_mb = out.stat().st_size / 1_048_576
        print(
            f"  {split}: {counts[split]:,} rows -> {out.name} ({size_mb:.1f} MB)",
            flush=True,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Thin CLI around `osm_polygon_selection.dataset_build.split_parquets`.

Writes `splits/{train,val,test}.parquet` so the HuggingFace dataset
viewer exposes each split as a separate tab. The actual stream-filter
logic lives in the package; this script is just argument parsing.

Defaults are derived from ``RuntimeConfig.from_env()`` (which honors
``$OSM_DATA_ROOT`` and ``$OSM_DATASET_DIR``). When the user passes
``--root X`` without ``--source`` or ``--out``, the script derives
``X/combined/all_world.parquet`` and ``X/splits`` from ``--root``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from osm_polygon_selection.dataset_build.split_parquets import write_split_parquets
from osm_polygon_selection.runtime_config import RuntimeConfig

_DEFAULT_CONFIG = RuntimeConfig.from_env()
DEFAULT_ROOT = _DEFAULT_CONFIG.dataset_root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    # --source and --out are derived from --root unless the user
    # explicitly overrode them. This makes `--root X` work as
    # expected (rather than being silently ignored when only --root
    # is supplied).
    if args.source is None:
        args.source = args.root / "combined" / "all_world.parquet"
    if args.out is None:
        args.out = args.root / "splits"

    print(f"reading {args.source}", flush=True)
    counts = write_split_parquets(args.source, args.out)

    for split in ("train", "val", "test"):
        out = args.out / f"{split}.parquet"
        if out.exists():
            size_mb = out.stat().st_size / 1_048_576
            print(
                f"  {split}: {counts[split]:,} rows -> {out.name} ({size_mb:.1f} MB)",
                flush=True,
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Split parquets CLI: write train/val/test parquet files for the HF viewer.

Thin wrapper around
``osm_polygon_selection.dataset_build.split_parquets.write_split_parquets``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from osm_polygon_selection.config import RuntimeConfig
from osm_polygon_selection.dataset_build.split_parquets import write_split_parquets


def _default_root() -> Path:
    return RuntimeConfig.from_env().dataset_root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=_default_root())
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

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
    raise SystemExit(main())

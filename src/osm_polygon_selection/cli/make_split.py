"""Make-split CLI: deterministic train/val/test split.

Thin wrapper around :func:`osm_polygon_selection.dataset_split.make_split`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from osm_polygon_selection.dataset_split import (
    DEFAULT_RATIOS,
    DEFAULT_ROOT,
    DEFAULT_SEED,
    make_split,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--train", type=float, default=DEFAULT_RATIOS["train"])
    parser.add_argument("--val", type=float, default=DEFAULT_RATIOS["val"])
    parser.add_argument("--test", type=float, default=DEFAULT_RATIOS["test"])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    ratios = {"train": args.train, "val": args.val, "test": args.test}
    out = make_split(root=args.root, seed=args.seed, ratios=ratios)
    n_alive = sum(
        1 for c in out["per_country_counts"].values() if sum(c.values()) > 0
    )
    print(json.dumps({"counts": out["counts"], "n_countries": n_alive}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

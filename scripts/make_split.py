"""CLI for the deterministic train/val/test split.

Thin wrapper around :func:`osm_polygon_selection.dataset_split.make_split`.
Usage::

    uv run python scripts/make_split.py
    uv run python scripts/make_split.py --root /path/to/dataset --seed 42

Re-exports ``_add_split_column_streaming`` and ``_write_combined_streaming``
for backwards-compat with existing tests that load this script as a module.
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
from osm_polygon_selection.dataset_split.combined import write_combined_streaming
from osm_polygon_selection.dataset_split.config import DEFAULT_RATIOS as _RATIOS
from osm_polygon_selection.dataset_split.per_parquet import (
    add_split_column_streaming,
)

_add_split_column_streaming = add_split_column_streaming


def _write_combined_streaming(
    root: Path,
    *,
    seed: int = DEFAULT_SEED,
    ratios: dict[str, float] | None = None,
    manifest: dict | None = None,
) -> int:
    if ratios is None:
        ratios = dict(_RATIOS)
    return write_combined_streaming(
        root, seed=seed, ratios=ratios, manifest=manifest,
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--train", type=float, default=DEFAULT_RATIOS["train"])
    p.add_argument("--val", type=float, default=DEFAULT_RATIOS["val"])
    p.add_argument("--test", type=float, default=DEFAULT_RATIOS["test"])
    return p.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    ratios = {"train": args.train, "val": args.val, "test": args.test}
    out = make_split(root=args.root, seed=args.seed, ratios=ratios)
    n_alive = sum(
        1 for c in out["per_country_counts"].values() if sum(c.values()) > 0
    )
    print(json.dumps({"counts": out["counts"], "n_countries": n_alive}, indent=2))

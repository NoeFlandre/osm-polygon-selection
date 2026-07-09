"""Thin entry point: deterministic train/val/test split.

Thin wrapper around :mod:`osm_polygon_selection.cli.make_split`.

Re-exports ``_add_split_column_streaming`` and ``_write_combined_streaming``
for backwards-compat with existing tests that load this script as a module.
"""

from __future__ import annotations

from osm_polygon_selection.cli.make_split import main, build_parser
from osm_polygon_selection.dataset_split.combined import write_combined_streaming
from osm_polygon_selection.dataset_split.config import DEFAULT_RATIOS as _RATIOS
from osm_polygon_selection.dataset_split.per_parquet import (
    add_split_column_streaming,
)

_add_split_column_streaming = add_split_column_streaming


def _write_combined_streaming(
    root,
    *,
    seed: int = 42,
    ratios: dict[str, float] | None = None,
    manifest: dict | None = None,
) -> int:
    if ratios is None:
        ratios = dict(_RATIOS)
    return write_combined_streaming(
        root, seed=seed, ratios=ratios, manifest=manifest,
    )


__all__ = [
    "_add_split_column_streaming",
    "_write_combined_streaming",
    "build_parser",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())

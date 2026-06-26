"""Shared I/O helpers for the polygon-selection pipeline.

Every stage reads a JSONL of polygon rows, transforms each row, and
writes a JSONL back out. This module centralizes that loop so each
stage file only contains its domain-specific transform.
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

Row = TypeVar("Row", dict, dict)
Transform = Callable[[Row], Row | None]


def stream_jsonl(
    in_path: Path,
    out_path: Path,
    transform: Transform,
) -> tuple[int, int]:
    """Stream a JSONL through transform, write kept rows to out_path.

    Args:
        in_path: input JSONL file (one polygon row per line).
        out_path: output JSONL file (created or overwritten).
        transform: function (row) -> row | None. If None, the row is
            dropped (filtered out). If a row, it is written.

    Returns:
        (kept_count, seen_count). seen - kept = dropped.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    kept = 0
    seen = 0
    with in_path.open() as fin, out_path.open("w") as fout:
        for line in fin:
            seen += 1
            row = json.loads(line)
            out_row = transform(row)
            if out_row is None:
                continue
            fout.write(json.dumps(out_row) + "\n")
            kept += 1
    return kept, seen

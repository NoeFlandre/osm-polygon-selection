"""Backwards-compat launcher for ``scripts/dataset/make_split.py``."""
from __future__ import annotations

import runpy
from pathlib import Path

from scripts.dataset.make_split import (  # noqa: F401
    _add_split_column_streaming,
    _write_combined_streaming,
    build_parser,
    main,
)

if __name__ == "__main__":
    runpy.run_path(
        str(Path(__file__).resolve().parent / "dataset" / "make_split.py"),
        run_name="__main__",
    )

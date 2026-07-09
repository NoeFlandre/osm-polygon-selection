"""Backwards-compat launcher for ``scripts/dataset/split_parquets.py``."""
from __future__ import annotations

import runpy
from pathlib import Path

from scripts.dataset.split_parquets import build_parser, main  # noqa: F401

if __name__ == "__main__":
    runpy.run_path(
        str(Path(__file__).resolve().parent / "dataset" / "split_parquets.py"),
        run_name="__main__",
    )

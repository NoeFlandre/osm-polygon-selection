"""Backwards-compat launcher for ``scripts/pipeline/stage0_extract.py``."""
import runpy
import sys
from pathlib import Path

runpy.run_path(
    str(Path(__file__).resolve().parent / "pipeline" / "stage0_extract.py"),
    run_name="__main__",
)

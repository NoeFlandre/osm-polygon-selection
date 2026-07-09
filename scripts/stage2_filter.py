"""Backwards-compat launcher for ``scripts/pipeline/stage2_filter.py``."""
import runpy
from pathlib import Path

runpy.run_path(
    str(Path(__file__).resolve().parent / "pipeline" / "stage2_filter.py"),
    run_name="__main__",
)

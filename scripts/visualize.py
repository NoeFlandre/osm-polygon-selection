"""Backwards-compat launcher for ``scripts/preview/visualize.py``."""
import runpy
from pathlib import Path

runpy.run_path(
    str(Path(__file__).resolve().parent / "preview" / "visualize.py"),
    run_name="__main__",
)

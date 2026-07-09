"""Backwards-compat launcher for ``scripts/pipeline/stage3_classify.py``."""
import runpy
from pathlib import Path

runpy.run_path(
    str(Path(__file__).resolve().parent / "pipeline" / "stage3_classify.py"),
    run_name="__main__",
)

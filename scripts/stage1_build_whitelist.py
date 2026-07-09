"""Backwards-compat launcher for ``scripts/pipeline/stage1_build_whitelist.py``."""
import runpy
from pathlib import Path

runpy.run_path(
    str(Path(__file__).resolve().parent / "pipeline" / "stage1_build_whitelist.py"),
    run_name="__main__",
)

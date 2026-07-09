"""Backwards-compat launcher for ``scripts/publishing/upload_to_hf.py``."""
import runpy
from pathlib import Path

runpy.run_path(
    str(Path(__file__).resolve().parent / "publishing" / "upload_to_hf.py"),
    run_name="__main__",
)

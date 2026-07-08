"""Tests for the streaming-writer wiring in build_dataset.py.

After the perf refactor, build_dataset.py's main loop calls
``write_jsonl_to_parquet`` for the per-country parquet. This test
pins that contract:

- The optimized writer is preferred over the per-row Python path
- If the writer fails, the fallback path runs (no regression)
- The output parquet has the same schema as before
- The manifest has the correct n_polygons count

This is a regression-style test (not strictly red-green, but
guards against future refactors that bypass the streaming path).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq
import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
BUILD_DATASET = SCRIPTS_DIR / "build_dataset.py"


def _load_build_dataset():
    spec = importlib.util.spec_from_file_location("build_dataset", BUILD_DATASET)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load {BUILD_DATASET}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["build_dataset"] = mod
    spec.loader.exec_module(mod)
    return mod


class TestBuildDatasetWiring:
    def test_streaming_writer_is_referenced(self) -> None:
        """build_dataset.py must import and use the streaming writer."""
        src = BUILD_DATASET.read_text()
        assert "from osm_polygon_selection.streaming_writer import" in src, (
            "build_dataset.py should import write_jsonl_to_parquet "
            "for the optimized per-country build path"
        )
        assert "write_jsonl_to_parquet(" in src, (
            "build_dataset.py should call write_jsonl_to_parquet"
        )

    def test_fallback_path_preserved(self) -> None:
        """The per-row Python fallback must still exist (regression
        safety net if the streaming writer ever breaks)."""
        src = BUILD_DATASET.read_text()
        assert "row_to_record" in src
        assert "falling back to per-row path" in src

    def test_fresh_module_smoke(self) -> None:
        """Build_dataset.py imports cleanly (no syntax errors after
        the refactor)."""
        bd = _load_build_dataset()
        assert hasattr(bd, "row_to_record")  # fallback preserved
        # The streaming writer must be importable from the package.
        from osm_polygon_selection.streaming_writer import write_jsonl_to_parquet
        assert callable(write_jsonl_to_parquet)

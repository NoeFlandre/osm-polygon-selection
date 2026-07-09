"""Tests for the JSONL -> pyarrow.Table parsing layer."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pyarrow as pa
import pytest

from osm_polygon_selection.streaming_writer import (
    _write_jsonl_to_parquet_python_json,
    write_jsonl_to_parquet,
)

from .conftest import _row, _write_jsonl


class TestOptimizedPath:
    """The optimized path must use pa.json.read_json (C-level parser)."""

    def test_uses_pa_json_for_parsing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from osm_polygon_selection.parquet_write import runner as runner_mod
        jsonl = tmp_path / "in.jsonl"
        out = tmp_path / "out.parquet"
        _write_jsonl(jsonl, [_row(i) for i in range(1, 11)])

        original = runner_mod.paj.read_json
        call_log: list[Path] = []
        def _tracking_read_json(source, *args, **kwargs):
            call_log.append(Path(str(source)))
            return original(source, *args, **kwargs)
        monkeypatch.setattr(
            runner_mod.paj, "read_json", _tracking_read_json,
        )

        from osm_polygon_selection.streaming_writer import write_jsonl_to_parquet
        write_jsonl_to_parquet(
            jsonl_path=jsonl,
            parquet_path=out,
            country="italy",
            extract_status="clean",
            pbf_date="2026-06-26",
        )
        assert call_log, "pa.json.read_json was never called; optimized path is not active"

    def test_faster_than_python_json_loads(self, tmp_path: Path) -> None:
        """The optimized writer should be measurably faster than
        calling json.loads() per row. Loose 1.2x threshold for CI."""
        jsonl = tmp_path / "in.jsonl"
        out_optimized = tmp_path / "optimized.parquet"
        out_python = tmp_path / "python.parquet"
        if out_optimized.exists():
            out_optimized.unlink()
        if out_python.exists():
            out_python.unlink()
        n_rows = 20_000
        with jsonl.open("w") as f:
            for i in range(1, n_rows + 1):
                f.write(json.dumps(_row(i)) + "\n")

        t0 = time.perf_counter()
        _write_jsonl_to_parquet_python_json(
            jsonl_path=jsonl,
            parquet_path=out_python,
            country="italy",
            extract_status="clean",
            pbf_date="2026-06-26",
        )
        py_elapsed = time.perf_counter() - t0

        t0 = time.perf_counter()
        write_jsonl_to_parquet(
            jsonl_path=jsonl,
            parquet_path=out_optimized,
            country="italy",
            extract_status="clean",
            pbf_date="2026-06-26",
        )
        opt_elapsed = time.perf_counter() - t0

        assert opt_elapsed < py_elapsed * 0.83, (
            f"optimized={opt_elapsed:.2f}s, python={py_elapsed:.2f}s; "
            f"speedup={py_elapsed / opt_elapsed:.2f}x; expected >= 1.2x"
        )


class TestGeometryEncoding:
    def test_geometry_wkt_passthrough(self, tmp_path: Path) -> None:
        import pyarrow.parquet as pq
        jsonl = tmp_path / "in.jsonl"
        out = tmp_path / "out.parquet"
        geom = "POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))"
        _write_jsonl(jsonl, [_row(1, geometry=geom)])
        write_jsonl_to_parquet(
            jsonl_path=jsonl,
            parquet_path=out,
            country="italy",
            extract_status="clean",
            pbf_date="2026-06-26",
            geometry_encoding="wkt",
        )
        t = pq.read_table(out)
        assert t.column("geometry_wkt").to_pylist() == [geom]

    def test_geometry_wkb_produces_binary(self, tmp_path: Path) -> None:
        import pyarrow as pa
        import pyarrow.parquet as pq
        jsonl = tmp_path / "in.jsonl"
        out = tmp_path / "out.parquet"
        _write_jsonl(jsonl, [_row(1)])
        write_jsonl_to_parquet(
            jsonl_path=jsonl,
            parquet_path=out,
            country="italy",
            extract_status="clean",
            pbf_date="2026-06-26",
            geometry_encoding="wkb",
        )
        t = pq.read_table(out)
        assert t.schema.field("geometry_wkb").type == pa.binary()
        assert len(t.column("geometry_wkb").to_pylist()[0]) > 0


class TestChunkSize:
    def test_default_chunk_size(self) -> None:
        from osm_polygon_selection.streaming_writer import CHUNK_SIZE
        assert CHUNK_SIZE == 50_000

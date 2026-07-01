"""Tests for the streaming JSONL → parquet writer.

TDD red phase: written before implementing the optimization in
``osm_polygon_selection.streaming_writer``.

This is the optimized replacement for the per-row Python loop in
``build_dataset.py``. It must:

- read a 03_classified.jsonl file line-by-line (no full-file load)
- convert each row to a record (parquet schema)
- write the parquet via ``ParquetWriter.write_batch`` in streaming
  chunks of e.g. 5_000 rows (constant memory)
- never materialize the full pyarrow Table in memory
- support both wkt and wkb geometry encodings
- backfill `matched_tag` using `vectorized_compute_matched_tags`
  (so legacy 03_classified.jsonl files without the column work)

Memory cost must be O(CHUNK_SIZE), not O(file_size).
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"


def _load_or_import_streaming():
    """Lazy import the streaming_writer module (TDD)."""
    from osm_polygon_selection.streaming_writer import (
        write_jsonl_to_parquet,
    )
    return write_jsonl_to_parquet


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def _row(
    osm_id: int,
    lon: float = 10.0,
    lat: float = 50.0,
    area: float = 1.0,
    tags: list[str] | None = None,
    matched_tag: str = "",
    continent: str = "Europe",
    size_bin: str = "small",
    geometry: str = "POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))",
) -> dict:
    return {
        "osm_id": osm_id,
        "osm_type": "way",
        "centroid": [lon, lat],
        "area_km2": area,
        "tags": tags or ["natural=water"],
        "matched_tag": matched_tag,
        "continent": continent,
        "size_bin": size_bin,
        "geometry": geometry,
    }


class TestWriteJsonlToParquet:
    def test_writes_all_rows(self, tmp_path: Path) -> None:
        write = _load_or_import_streaming()
        jsonl = tmp_path / "in.jsonl"
        out = tmp_path / "out.parquet"
        rows = [_row(i) for i in range(1, 11)]
        _write_jsonl(jsonl, rows)
        n = write(
            jsonl_path=jsonl,
            parquet_path=out,
            country="italy",
            extract_status="clean",
            pbf_date="2026-06-26",
        )
        assert n == 10
        t = pq.read_table(out)
        assert t.num_rows == 10

    def test_columns_match_schema(self, tmp_path: Path) -> None:
        write = _load_or_import_streaming()
        jsonl = tmp_path / "in.jsonl"
        out = tmp_path / "out.parquet"
        _write_jsonl(jsonl, [_row(1)])
        write(
            jsonl_path=jsonl,
            parquet_path=out,
            country="italy",
            extract_status="clean",
            pbf_date="2026-06-26",
        )
        t = pq.read_table(out)
        expected_cols = {
            "osm_id", "osm_type", "centroid_lon", "centroid_lat",
            "area_km2", "tags", "matched_tag", "continent", "size_bin",
            "country", "extract_status", "pbf_date", "geometry_wkt",
        }
        assert set(t.schema.names) == expected_cols

    def test_metadata_columns_constant(self, tmp_path: Path) -> None:
        write = _load_or_import_streaming()
        jsonl = tmp_path / "in.jsonl"
        out = tmp_path / "out.parquet"
        _write_jsonl(jsonl, [_row(1), _row(2)])
        write(
            jsonl_path=jsonl,
            parquet_path=out,
            country="france",
            extract_status="clean",
            pbf_date="2026-06-26",
        )
        t = pq.read_table(out)
        countries = set(t.column("country").to_pylist())
        assert countries == {"france"}
        statuses = set(t.column("extract_status").to_pylist())
        assert statuses == {"clean"}
        dates = set(t.column("pbf_date").to_pylist())
        assert dates == {"2026-06-26"}

    def test_centroid_split_into_lon_lat(self, tmp_path: Path) -> None:
        write = _load_or_import_streaming()
        jsonl = tmp_path / "in.jsonl"
        out = tmp_path / "out.parquet"
        _write_jsonl(jsonl, [_row(1, lon=12.345, lat=45.678)])
        write(
            jsonl_path=jsonl,
            parquet_path=out,
            country="italy",
            extract_status="clean",
            pbf_date="2026-06-26",
        )
        t = pq.read_table(out)
        assert t.column("centroid_lon").to_pylist() == [12.345]
        assert t.column("centroid_lat").to_pylist() == [45.678]

    def test_matched_tag_backfilled_when_missing(self, tmp_path: Path) -> None:
        """Legacy 03_classified.jsonl files don't have matched_tag.
        The streaming writer must compute it from row.tags against
        the whitelist (vectorized)."""
        from osm_polygon_selection.streaming_writer import (
            write_jsonl_to_parquet,
        )
        # Write a tiny whitelist with one tag.
        wl = tmp_path / "whitelist.json"
        wl.write_text(json.dumps(["natural=water"]))

        jsonl = tmp_path / "in.jsonl"
        out = tmp_path / "out.parquet"
        # Two rows: one matches the whitelist, one doesn't.
        _write_jsonl(jsonl, [
            _row(1, tags=["name=Lake", "natural=water"]),
            _row(2, tags=["place=islet"]),
        ])
        write_jsonl_to_parquet(
            jsonl_path=jsonl,
            parquet_path=out,
            country="italy",
            extract_status="clean",
            pbf_date="2026-06-26",
            whitelist_path=wl,
        )
        t = pq.read_table(out)
        matched = t.column("matched_tag").to_pylist()
        assert matched == ["natural=water", ""]

    def test_matched_tag_passthrough_when_set(self, tmp_path: Path) -> None:
        from osm_polygon_selection.streaming_writer import write_jsonl_to_parquet
        wl = tmp_path / "whitelist.json"
        wl.write_text(json.dumps(["natural=water"]))

        jsonl = tmp_path / "in.jsonl"
        out = tmp_path / "out.parquet"
        # matched_tag is pre-set; the writer must NOT overwrite it.
        _write_jsonl(jsonl, [
            _row(1, tags=["name=Lake"], matched_tag="landuse=forest"),
        ])
        write_jsonl_to_parquet(
            jsonl_path=jsonl,
            parquet_path=out,
            country="italy",
            extract_status="clean",
            pbf_date="2026-06-26",
            whitelist_path=wl,
        )
        t = pq.read_table(out)
        assert t.column("matched_tag").to_pylist() == ["landuse=forest"]

    def test_handles_empty_jsonl(self, tmp_path: Path) -> None:
        from osm_polygon_selection.streaming_writer import write_jsonl_to_parquet
        jsonl = tmp_path / "in.jsonl"
        out = tmp_path / "out.parquet"
        jsonl.write_text("")
        n = write_jsonl_to_parquet(
            jsonl_path=jsonl,
            parquet_path=out,
            country="italy",
            extract_status="clean",
            pbf_date="2026-06-26",
        )
        assert n == 0
        # Output file should still exist (with no row groups).
        assert out.is_file()

    def test_skips_malformed_rows(self, tmp_path: Path) -> None:
        from osm_polygon_selection.streaming_writer import write_jsonl_to_parquet
        jsonl = tmp_path / "in.jsonl"
        out = tmp_path / "out.parquet"
        with jsonl.open("w") as f:
            f.write(json.dumps(_row(1)) + "\n")
            f.write("{ not valid json\n")
            f.write(json.dumps(_row(2)) + "\n")
        n = write_jsonl_to_parquet(
            jsonl_path=jsonl,
            parquet_path=out,
            country="italy",
            extract_status="clean",
            pbf_date="2026-06-26",
        )
        assert n == 2
        t = pq.read_table(out)
        assert t.num_rows == 2
        assert t.column("osm_id").to_pylist() == [1, 2]

    def test_uses_pa_table_chunked_writer(self, tmp_path: Path) -> None:
        """The streaming writer must use ``pa.table({col: list}, schema)``
        (NOT ``pa.Table.from_pylist(list_of_dicts)`` on the full row set)
        and call ``ParquetWriter.write_batch`` per chunk.

        We verify the streaming contract by checking the output has
        multiple row groups (one per chunk) when the input has more
        rows than CHUNK_SIZE. The default CHUNK_SIZE is 50_000;
        we override to 100 for this test by writing 250 rows.
        """
        from osm_polygon_selection.streaming_writer import write_jsonl_to_parquet
        jsonl = tmp_path / "in.jsonl"
        out = tmp_path / "out.parquet"
        _write_jsonl(jsonl, [_row(i) for i in range(1, 251)])
        write_jsonl_to_parquet(
            jsonl_path=jsonl,
            parquet_path=out,
            country="italy",
            extract_status="clean",
            pbf_date="2026-06-26",
            chunk_size=100,
        )
        pf = pq.ParquetFile(out)
        # 250 rows / 100 per chunk = 3 row groups.
        assert pf.num_row_groups == 3, (
            f"expected 3 row groups (chunked streaming), got {pf.num_row_groups}"
        )

    def test_geometry_wkt_passthrough(self, tmp_path: Path) -> None:
        from osm_polygon_selection.streaming_writer import write_jsonl_to_parquet
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

    def test_large_input_streamed(self, tmp_path: Path) -> None:
        """The writer must handle 50k rows in streaming mode without
        materializing the full table."""
        from osm_polygon_selection.streaming_writer import write_jsonl_to_parquet
        jsonl = tmp_path / "in.jsonl"
        out = tmp_path / "out.parquet"
        n_rows = 50_000
        with jsonl.open("w") as f:
            for i in range(1, n_rows + 1):
                f.write(json.dumps(_row(i)) + "\n")
        n = write_jsonl_to_parquet(
            jsonl_path=jsonl,
            parquet_path=out,
            country="italy",
            extract_status="clean",
            pbf_date="2026-06-26",
        )
        assert n == n_rows
        t = pq.read_table(out)
        assert t.num_rows == n_rows

    def test_faster_than_python_json_loads(self, tmp_path: Path) -> None:
        """Sanity check: the optimized writer should be measurably
        faster than calling json.loads() per row (Python's stdlib
        JSON parser). The pyarrow C-level JSON parser
        (``pa.json.read_json``) is much faster.

        This test runs both paths on 20k rows and asserts the
        optimized path is at least 1.2x faster (loose threshold
        for CI noise).
        """
        from osm_polygon_selection.streaming_writer import (
            _write_jsonl_to_parquet_python_json,
            write_jsonl_to_parquet,
        )
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

        # Python json.loads path (for benchmarking only).
        t0 = time.perf_counter()
        _write_jsonl_to_parquet_python_json(
            jsonl_path=jsonl,
            parquet_path=out_python,
            country="italy",
            extract_status="clean",
            pbf_date="2026-06-26",
        )
        py_elapsed = time.perf_counter() - t0

        # Optimized pa.json.read_json path.
        t0 = time.perf_counter()
        write_jsonl_to_parquet(
            jsonl_path=jsonl,
            parquet_path=out_optimized,
            country="italy",
            extract_status="clean",
            pbf_date="2026-06-26",
        )
        opt_elapsed = time.perf_counter() - t0

        # The optimized path should be at least 1.2x faster.
        # (On a typical laptop it's ~2-3x.)
        assert opt_elapsed < py_elapsed * 0.83, (
            f"optimized={opt_elapsed:.2f}s, python={py_elapsed:.2f}s; "
            f"speedup={py_elapsed / opt_elapsed:.2f}x; expected >= 1.2x"
        )

    def test_uses_pa_json_for_parsing(self, tmp_path: Path, monkeypatch) -> None:
        """Pin that the optimized path uses pa.json.read_json
        (the C-level parser), NOT the per-row json.loads path.

        We monkeypatch ``osm_polygon_selection.streaming_writer.paj.read_json``
        (the module-level reference) to track calls; the optimized
        path must call it at least once.
        """
        from osm_polygon_selection import streaming_writer
        jsonl = tmp_path / "in.jsonl"
        out = tmp_path / "out.parquet"
        _write_jsonl(jsonl, [_row(i) for i in range(1, 11)])

        # Track paj.read_json calls on the module-level import.
        original = streaming_writer.paj.read_json
        call_log: list[Path] = []
        def _tracking_read_json(source, *args, **kwargs):
            call_log.append(Path(str(source)))
            return original(source, *args, **kwargs)
        monkeypatch.setattr(
            streaming_writer.paj, "read_json", _tracking_read_json
        )

        streaming_writer.write_jsonl_to_parquet(
            jsonl_path=jsonl,
            parquet_path=out,
            country="italy",
            extract_status="clean",
            pbf_date="2026-06-26",
        )
        assert call_log, "pa.json.read_json was never called; optimized path is not active"

    def test_default_compression_is_zstd(self, tmp_path: Path) -> None:
        """Default compression must be zstd (smaller than snappy,
        ~36% on typical OSM data) at level 1 (fast decode).
        """
        from osm_polygon_selection.streaming_writer import write_jsonl_to_parquet
        jsonl = tmp_path / "in.jsonl"
        out = tmp_path / "out.parquet"
        _write_jsonl(jsonl, [_row(i) for i in range(1, 101)])
        write_jsonl_to_parquet(
            jsonl_path=jsonl,
            parquet_path=out,
            country="italy",
            extract_status="clean",
            pbf_date="2026-06-26",
        )
        meta = pq.read_metadata(out)
        # 0=uncompressed, 1=snappy, 2=gzip, 3=lzo, 4=brotli, 5=zstd, 6=lz4
        codec_names = {
            0: "uncompressed", 1: "snappy", 2: "gzip", 3: "lzo",
            4: "brotli", 5: "zstd", 6: "lz4",
        }
        assert meta.row_group(0).column(0).compression in ("ZSTD", "zstd"), (
            f"expected zstd compression, got {codec_names.get(meta.row_group(0).column(0).compression, meta.row_group(0).column(0).compression)}"
        )

    def test_explicit_compression_override(self, tmp_path: Path) -> None:
        """The compression param must override the default (test
        we can still write snappy for legacy compat)."""
        from osm_polygon_selection.streaming_writer import write_jsonl_to_parquet
        jsonl = tmp_path / "in.jsonl"
        out = tmp_path / "out.parquet"
        _write_jsonl(jsonl, [_row(i) for i in range(1, 101)])
        write_jsonl_to_parquet(
            jsonl_path=jsonl,
            parquet_path=out,
            country="italy",
            extract_status="clean",
            pbf_date="2026-06-26",
            compression="snappy",
        )
        meta = pq.read_metadata(out)
        assert meta.row_group(0).column(0).compression in ("SNAPPY", "snappy")

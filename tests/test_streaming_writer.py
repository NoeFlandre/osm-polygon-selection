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

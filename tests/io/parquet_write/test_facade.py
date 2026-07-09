"""Tests for ``write_jsonl_to_parquet`` (the public facade)."""

from __future__ import annotations

import json
from pathlib import Path

from osm_polygon_selection.streaming_writer import (
    write_jsonl_to_parquet,
)

from .conftest import (
    _read_parquet,
    _row,
    _row_group_count,
    _write_jsonl,
)


class TestWriteJsonlToParquet:
    def test_writes_all_rows(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "in.jsonl"
        out = tmp_path / "out.parquet"
        rows = [_row(i) for i in range(1, 11)]
        _write_jsonl(jsonl, rows)
        n = write_jsonl_to_parquet(
            jsonl_path=jsonl,
            parquet_path=out,
            country="italy",
            extract_status="clean",
            pbf_date="2026-06-26",
        )
        assert n == 10
        t = _read_parquet(out)
        assert t.num_rows == 10

    def test_columns_match_schema(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "in.jsonl"
        out = tmp_path / "out.parquet"
        _write_jsonl(jsonl, [_row(1)])
        write_jsonl_to_parquet(
            jsonl_path=jsonl,
            parquet_path=out,
            country="italy",
            extract_status="clean",
            pbf_date="2026-06-26",
        )
        t = _read_parquet(out)
        expected_cols = {
            "osm_id", "osm_type", "centroid_lon", "centroid_lat",
            "area_km2", "tags", "matched_tag", "continent", "size_bin",
            "country", "extract_status", "pbf_date", "geometry_wkt",
        }
        assert set(t.schema.names) == expected_cols

    def test_metadata_columns_constant(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "in.jsonl"
        out = tmp_path / "out.parquet"
        _write_jsonl(jsonl, [_row(1), _row(2)])
        write_jsonl_to_parquet(
            jsonl_path=jsonl,
            parquet_path=out,
            country="france",
            extract_status="clean",
            pbf_date="2026-06-26",
        )
        t = _read_parquet(out)
        assert set(t.column("country").to_pylist()) == {"france"}
        assert set(t.column("extract_status").to_pylist()) == {"clean"}
        assert set(t.column("pbf_date").to_pylist()) == {"2026-06-26"}

    def test_centroid_split_into_lon_lat(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "in.jsonl"
        out = tmp_path / "out.parquet"
        _write_jsonl(jsonl, [_row(1, lon=12.345, lat=45.678)])
        write_jsonl_to_parquet(
            jsonl_path=jsonl,
            parquet_path=out,
            country="italy",
            extract_status="clean",
            pbf_date="2026-06-26",
        )
        t = _read_parquet(out)
        assert t.column("centroid_lon").to_pylist() == [12.345]
        assert t.column("centroid_lat").to_pylist() == [45.678]

    def test_handles_empty_jsonl(self, tmp_path: Path) -> None:
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
        assert out.is_file()

    def test_skips_malformed_rows(self, tmp_path: Path) -> None:
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
        t = _read_parquet(out)
        assert t.num_rows == 2
        assert t.column("osm_id").to_pylist() == [1, 2]

    def test_uses_chunked_writer(self, tmp_path: Path) -> None:
        """250 rows / chunk_size=100 -> 3 row groups (streaming contract)."""
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
        nrg = _row_group_count(out)
        assert nrg == 3, f"expected 3 row groups, got {nrg}"

    def test_large_input_streamed(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "in.jsonl"
        out = tmp_path / "out.parquet"
        n_rows = 50_000
        with jsonl.open("w") as f:
            for i in range(1, n_rows + 1):
                f.write("{" + f'"osm_id":{i},"osm_type":"way","centroid":[10,50],"area_km2":1,"tags":["natural=water"],"matched_tag":"","continent":"Europe","size_bin":"small","geometry":"POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))"' + "}\n")
        n = write_jsonl_to_parquet(
            jsonl_path=jsonl,
            parquet_path=out,
            country="italy",
            extract_status="clean",
            pbf_date="2026-06-26",
        )
        assert n == n_rows
        t = _read_parquet(out)
        assert t.num_rows == n_rows

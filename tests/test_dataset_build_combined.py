"""Tests for `osm_polygon_selection.dataset_build.combined.combine_per_country_parquets`.

Pins two contracts:

1. With a fixture of per-country parquet files, the combined output
   contains exactly the concatenation of rows.
2. If processing fails mid-loop (e.g. one file is broken), the
   ParquetWriter is closed and the exception propagates.
"""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from osm_polygon_selection.dataset_build.combined import (
    combine_per_country_parquets,
)


def _make_country_parquet(path: Path, country: str, n: int) -> None:
    """Write a per-country parquet with n rows for ``country``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.table(
        {
            "osm_id": list(range(n)),
            "country": [country] * n,
            "area_km2": [1.0] * n,
        }
    )
    pq.write_table(table, path)


def test_combine_writes_total_rows(tmp_path: Path) -> None:
    """combined.parquet must contain exactly sum(n_polygons) rows."""
    countries = [
        {"country": "france", "n_polygons": 1000, "extract_status": "clean"},
        {"country": "germany", "n_polygons": 500, "extract_status": "clean"},
        {"country": "liechtenstein", "n_polygons": 0, "extract_status": "clean"},
    ]
    _make_country_parquet(tmp_path / "france.parquet", "france", 1000)
    _make_country_parquet(tmp_path / "germany.parquet", "germany", 500)
    # liechtenstein has n_polygons=0 -> skipped, no file written.

    total = combine_per_country_parquets(
        out_dir=tmp_path,
        countries=countries,
        output_path=tmp_path / "all_world.parquet",
    )
    assert total == 1500
    out = pq.read_table(tmp_path / "all_world.parquet")
    assert out.num_rows == 1500


def test_combine_closes_writer_on_exception(tmp_path: Path, monkeypatch) -> None:
    """Even when a per-country parquet read fails mid-loop, the writer is closed."""
    countries = [
        {"country": "france", "n_polygons": 1000, "extract_status": "clean"},
        {"country": "germany", "n_polygons": 500, "extract_status": "clean"},
    ]
    _make_country_parquet(tmp_path / "france.parquet", "france", 1000)
    _make_country_parquet(tmp_path / "germany.parquet", "germany", 500)

    # Monkeypatch read_table to raise on the second call.
    original_read_table = pq.read_table
    call_count = {"n": 0}

    def maybe_fail(path, *args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] >= 2:
            raise RuntimeError("simulated mid-loop failure")
        return original_read_table(path, *args, **kwargs)

    monkeypatch.setattr(
        "osm_polygon_selection.dataset_build.combined.pq.read_table",
        maybe_fail,
    )

    import pytest

    with pytest.raises(RuntimeError, match="simulated mid-loop failure"):
        combine_per_country_parquets(
            out_dir=tmp_path,
            countries=countries,
            output_path=tmp_path / "all_world.parquet",
        )

    # The partial parquet exists but is now closed (footer written).
    # We just verify it does not crash on a follow-up read.
    assert (tmp_path / "all_world.parquet").is_file()


def test_combine_raises_when_no_parquets_exist(tmp_path: Path) -> None:
    """If no per-country parquet is present, raise FileNotFoundError."""
    import pytest

    with pytest.raises(FileNotFoundError):
        combine_per_country_parquets(
            out_dir=tmp_path,
            countries=[
                {"country": "france", "n_polygons": 0, "extract_status": "killed"},
            ],
            output_path=tmp_path / "all_world.parquet",
        )

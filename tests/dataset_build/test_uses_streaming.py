"""Package-level test: the build runner uses the streaming writer.

The optimized writer is preferred over the per-row Python path.
If the writer fails or yields 0, the runner falls back to the
per-row path (which calls ``row_to_record``). These are now
tested at the package boundary rather than via script-source
grep.
"""

from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from osm_polygon_selection.dataset_build.runner import _process_classified_country


@pytest.fixture
def classified_country_dir(tmp_path: Path) -> Path:
    """Build a PROC/<country> with 03_classified.jsonl + run.json."""
    proc_country = tmp_path / "monaco"
    proc_country.mkdir()
    rows = [
        {
            "osm_id": i, "osm_type": "way", "centroid": [9.5 + i * 0.001, 47.05],
            "area_km2": 0.5, "tags": ["landuse=forest"], "continent": "Europe",
            "size_bin": "small", "geometry": "POLYGON((0 0,1 0,1 1,0 1,0 0))",
        }
        for i in range(3)
    ]
    with (proc_country / "03_classified.jsonl").open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    (proc_country / "run.json").write_text(json.dumps({"ok": True}))
    return proc_country


def test_streaming_path_writes_parquet(
    monkeypatch: pytest.MonkeyPatch, classified_country_dir: Path, tmp_path: Path
) -> None:
    """The streaming writer path produces a per-country parquet."""
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    row = _process_classified_country(
        classified_country_dir,
        out_dir,
        geometry_encoding="wkt",
        whitelist_path=Path("/nonexistent"),
    )
    assert row is not None
    assert row["n_polygons"] == 3
    assert (out_dir / "monaco.parquet").is_file()
    table = pq.read_table(out_dir / "monaco.parquet")
    assert table.num_rows == 3


def test_fallback_path_writes_parquet(
    monkeypatch: pytest.MonkeyPatch, classified_country_dir: Path, tmp_path: Path
) -> None:
    """If the streaming writer raises, the per-row fallback still writes."""
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    def _broken_writer(*_args, **_kwargs) -> int:
        raise RuntimeError("simulated streaming failure")

    from osm_polygon_selection.dataset_build import runner
    monkeypatch.setattr(runner, "write_jsonl_to_parquet", _broken_writer)

    row = _process_classified_country(
        classified_country_dir,
        out_dir,
        geometry_encoding="wkt",
        whitelist_path=Path("/nonexistent"),
    )
    assert row is not None
    assert row["n_polygons"] == 3
    assert (out_dir / "monaco.parquet").is_file()


def test_zero_yield_returns_manifest_row(
    monkeypatch: pytest.MonkeyPatch, classified_country_dir: Path, tmp_path: Path
) -> None:
    """If both paths yield 0, the runner returns a zero-yield manifest row."""
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    def _zero_writer(*_args, **_kwargs) -> int:
        return 0

    from osm_polygon_selection.dataset_build import runner
    monkeypatch.setattr(runner, "write_jsonl_to_parquet", _zero_writer)

    # Empty the input file so the per-row fallback also yields 0.
    (classified_country_dir / "03_classified.jsonl").write_text("")

    row = _process_classified_country(
        classified_country_dir,
        out_dir,
        geometry_encoding="wkt",
        whitelist_path=Path("/nonexistent"),
    )
    assert row is not None
    assert row["n_polygons"] == 0
    assert row["extract_status"] == "clean"
    # The stale parquet (if any) was removed before the fallback ran.
    assert not (out_dir / "monaco.parquet").is_file()

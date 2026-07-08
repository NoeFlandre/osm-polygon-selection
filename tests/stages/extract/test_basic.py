"""Basic happy-path tests for the extract stage (split from test_extract.py)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from ._helpers import _drive, _make_obj, _read_jsonl_rows


def test_extract_writes_one_row_per_accepted_object(tmp_path: Path) -> None:
    objs = [_make_obj(1), _make_obj(2), _make_obj(3)]
    out, _, _ = _drive(tmp_path, objs)
    rows = _read_jsonl_rows(out)
    assert [r["id"] for r in rows] == [1, 2, 3]


def test_extract_wal_records_all_seen_ids(tmp_path: Path) -> None:
    objs = [_make_obj(1), _make_obj(2)]
    _, wal, _ = _drive(tmp_path, objs)
    seen = sorted(int(x) for x in wal.read_text().strip().split("\n") if x)
    assert seen == [1, 2]


def test_extract_limit_stops_after_n_writes(tmp_path: Path) -> None:
    objs = [_make_obj(i) for i in range(1, 11)]
    out, _, log = _drive(tmp_path, objs, limit=3)
    assert len(_read_jsonl_rows(out)) == 3
    log_data = json.loads(log.read_text())
    assert log_data["polygons_written"] == 3
    assert log_data["limit_reached"] is True


def test_extract_limit_none_runs_to_completion(tmp_path: Path) -> None:
    objs = [_make_obj(i) for i in range(1, 6)]
    out, _, log = _drive(tmp_path, objs, limit=None)
    assert len(_read_jsonl_rows(out)) == 5
    log_data = json.loads(log.read_text())
    assert log_data["polygons_written"] == 5
    assert log_data["limit_reached"] is False


def test_extract_is_idempotent_when_run_twice(tmp_path: Path) -> None:
    pbf = tmp_path / "fake.osm.pbf"
    pbf.touch()
    out = tmp_path / "out.jsonl"
    objs = [_make_obj(i) for i in range(1, 6)]

    def fake_record(obj, fout, drops):
        fout.write(json.dumps({"id": obj.id}) + "\n")
        return 1

    from osm_polygon_selection.stages.extract import extract

    with patch(
        "osm_polygon_selection.stages.extract.osmium.FileProcessor",
    ) as fp_cls, patch(
        "osm_polygon_selection.stages.extract._record",
        side_effect=fake_record,
    ):
        fp_instance = MagicMock()
        fp_instance.with_areas.return_value = iter(objs)
        fp_cls.return_value = fp_instance
        extract(pbf, out)
    first_count = len(_read_jsonl_rows(out))

    with patch(
        "osm_polygon_selection.stages.extract.osmium.FileProcessor",
    ) as fp_cls, patch(
        "osm_polygon_selection.stages.extract._record",
        side_effect=fake_record,
    ):
        fp_instance = MagicMock()
        fp_instance.with_areas.return_value = iter(objs)
        fp_cls.return_value = fp_instance
        extract(pbf, out)
    second_count = len(_read_jsonl_rows(out))

    assert first_count == 5
    assert second_count == 5
    log = json.loads(out.with_suffix(out.suffix + ".run.json").read_text())
    assert log["polygons_written"] == 0

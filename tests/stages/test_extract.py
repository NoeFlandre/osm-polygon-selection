"""Tests for the extract stage's audit, resume, and limit behavior.

These tests focus on the *control flow* (seen-set, limit, run log,
progress file) rather than the geometry path. Liechtenstein is the
end-to-end real-data test for the geometry path.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from osm_polygon_selection.stages.extract import extract


def _make_obj(osm_id: int) -> MagicMock:
    """Mock OSM object that the patched _record will accept.

    We patch _record to be a side_effect that writes a row to fout
    (mimicking the real one) and returns 1. So this object only needs
    to have a unique .id.
    """
    obj = MagicMock()
    obj.id = osm_id
    obj.is_area.return_value = True
    return obj


def _make_dropped_obj(osm_id: int) -> MagicMock:
    obj = MagicMock()
    obj.id = osm_id
    obj.is_area.return_value = False  # -> "not an area" drop
    return obj


def _drive(
    tmp_path: Path,
    mock_objects: list[MagicMock],
    limit: int | None = None,
    pbf_name: str = "fake.osm.pbf",
):
    """Run extract() with mocked osmium AND a fake _record that writes rows.

    _record is replaced with a function that writes a sentinel JSON
    line "{id: <id>}" to fout and returns 1, so we test the seen-set,
    limit, and run-log logic without needing real geometry.
    """
    pbf = tmp_path / pbf_name
    pbf.touch()
    out = tmp_path / "out.jsonl"

    def fake_record(obj, fout, drops):
        # Sentinel row (just enough to test JSONL line count).
        fout.write(json.dumps({"id": obj.id}) + "\n")
        return 1

    with patch(
        "osm_polygon_selection.stages.extract.osmium.FileProcessor",
    ) as fp_cls, patch(
        "osm_polygon_selection.stages.extract._record",
        side_effect=fake_record,
    ):
        fp_instance = MagicMock()
        fp_instance.with_areas.return_value = iter(mock_objects)
        fp_cls.return_value = fp_instance
        extract(pbf, out, limit=limit)

    return (
        out,
        out.with_suffix(out.suffix + ".seen_ids"),
        out.with_suffix(out.suffix + ".run.json"),
    )


def _read_jsonl_rows(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().split("\n") if l]


# ---- Basic happy path ----

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


# ---- --limit ----

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


# ---- Resume: skip ALL seen ids (kept + dropped) ----

def test_resume_skips_already_seen_kept_ids(tmp_path: Path) -> None:
    out = tmp_path / "out.jsonl"
    wal = out.with_suffix(out.suffix + ".seen_ids")
    out.parent.mkdir(parents=True, exist_ok=True)
    wal.write_text("42\n")  # pre-seed

    pbf = tmp_path / "fake.osm.pbf"
    pbf.touch()
    objs = [_make_obj(42), _make_obj(43)]

    def fake_record(obj, fout, drops):
        fout.write(json.dumps({"id": obj.id}) + "\n")
        return 1

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
    rows = _read_jsonl_rows(out)
    assert [r["id"] for r in rows] == [43]
    log_data = json.loads(out.with_suffix(out.suffix + ".run.json").read_text())
    assert log_data["polygons_skipped_resume"] == 1
    assert log_data["polygons_written"] == 1


def test_resume_does_not_re_evaluate_dropped_ids(tmp_path: Path) -> None:
    """A 'dropped' id is in the seen set -> skipped on resume, not re-evaluated."""
    out = tmp_path / "out.jsonl"
    wal = out.with_suffix(out.suffix + ".seen_ids")
    out.parent.mkdir(parents=True, exist_ok=True)
    wal.write_text("99\n")  # pre-seed: 99 was seen in a prior run (and dropped)
    obj99 = _make_dropped_obj(99)
    obj100 = _make_obj(100)
    pbf = tmp_path / "fake.osm.pbf"
    pbf.touch()

    def fake_record(obj, fout, drops):
        fout.write(json.dumps({"id": obj.id}) + "\n")
        return 1

    with patch(
        "osm_polygon_selection.stages.extract.osmium.FileProcessor",
    ) as fp_cls, patch(
        "osm_polygon_selection.stages.extract._record",
        side_effect=fake_record,
    ):
        fp_instance = MagicMock()
        fp_instance.with_areas.return_value = iter([obj99, obj100])
        fp_cls.return_value = fp_instance
        extract(pbf, out)
    # id=99 was skipped (not re-evaluated). id=100 was written.
    rows = _read_jsonl_rows(out)
    assert [r["id"] for r in rows] == [100]
    log_data = json.loads(out.with_suffix(out.suffix + ".run.json").read_text())
    assert log_data["polygons_written"] == 1
    assert log_data["polygons_skipped_resume"] == 1
    # No drops recorded - id=99 was skipped before re-evaluation.
    assert log_data["drops"] == {}


def test_resume_with_limit_writes_only_new_polygons(tmp_path: Path) -> None:
    out = tmp_path / "out.jsonl"
    wal = out.with_suffix(out.suffix + ".seen_ids")
    out.parent.mkdir(parents=True, exist_ok=True)
    wal.write_text("\n".join(str(i) for i in range(1, 6)) + "\n")
    objs = [_make_obj(i) for i in range(6, 16)]
    pbf = tmp_path / "fake.osm.pbf"
    pbf.touch()

    def fake_record(obj, fout, drops):
        fout.write(json.dumps({"id": obj.id}) + "\n")
        return 1

    with patch(
        "osm_polygon_selection.stages.extract.osmium.FileProcessor",
    ) as fp_cls, patch(
        "osm_polygon_selection.stages.extract._record",
        side_effect=fake_record,
    ):
        fp_instance = MagicMock()
        fp_instance.with_areas.return_value = iter(objs)
        fp_cls.return_value = fp_instance
        extract(pbf, out, limit=3)
    rows = _read_jsonl_rows(out)
    assert len(rows) == 3


# ---- Run log (audit) ----

def test_run_log_contains_full_audit_metadata(tmp_path: Path) -> None:
    pbf = tmp_path / "fake.osm.pbf"
    pbf.touch()
    out = tmp_path / "out.jsonl"
    objs = [_make_obj(i) for i in range(1, 4)]
    with patch(
        "osm_polygon_selection.stages.extract.osmium.FileProcessor",
    ) as fp_cls, patch(
        "osm_polygon_selection.stages.extract._record", return_value=1,
    ):
        fp_instance = MagicMock()
        fp_instance.with_areas.return_value = iter(objs)
        fp_cls.return_value = fp_instance
        extract(pbf, out, limit=2)
    log_path = out.with_suffix(out.suffix + ".run.json")
    log = json.loads(log_path.read_text())
    for field in [
        "pbf_path", "pbf_size_bytes", "output_path", "wal_path",
        "start_time_utc", "end_time_utc", "elapsed_seconds",
        "polygons_written", "polygons_skipped_resume", "limit",
        "limit_reached", "drops", "total_osm_ids_seen", "peak_rss_mb",
    ]:
        assert field in log, f"missing audit field: {field}"
    assert log["polygons_written"] == 2
    assert log["limit"] == 2
    assert log["limit_reached"] is True

def test_run_log_total_seen_includes_written_and_dropped(tmp_path: Path) -> None:
    pbf = tmp_path / "fake.osm.pbf"
    pbf.touch()
    out = tmp_path / "out.jsonl"
    # 2 written + 1 dropped (not_an_area) = 3 total seen
    obj1 = _make_obj(1)
    obj2 = _make_obj(2)
    obj3 = _make_dropped_obj(3)

    def fake_record(obj, fout, drops):
        if not obj.is_area():
            return 0  # dropped
        fout.write(json.dumps({"id": obj.id}) + "\n")
        return 1

    with patch(
        "osm_polygon_selection.stages.extract.osmium.FileProcessor",
    ) as fp_cls, patch(
        "osm_polygon_selection.stages.extract._record",
        side_effect=fake_record,
    ):
        fp_instance = MagicMock()
        fp_instance.with_areas.return_value = iter([obj1, obj2, obj3])
        fp_cls.return_value = fp_instance
        extract(pbf, out)
    log = json.loads(out.with_suffix(out.suffix + ".run.json").read_text())
    assert log["polygons_written"] == 2
    assert log["total_osm_ids_seen"] == 3


# ---- Idempotency ----

def test_extract_is_idempotent_when_run_twice(tmp_path: Path) -> None:
    pbf = tmp_path / "fake.osm.pbf"
    pbf.touch()
    out = tmp_path / "out.jsonl"
    objs = [_make_obj(i) for i in range(1, 6)]

    def fake_record(obj, fout, drops):
        fout.write(json.dumps({"id": obj.id}) + "\n")
        return 1

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
    assert second_count == 5  # JSONL unchanged
    log = json.loads(out.with_suffix(out.suffix + ".run.json").read_text())
    assert log["polygons_written"] == 0
    assert log["polygons_skipped_resume"] == 5

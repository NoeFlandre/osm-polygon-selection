"""Run-log / audit tests (split from test_extract.py)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from osm_polygon_selection.stages.extract import extract

from ._helpers import _make_dropped_obj, _make_obj


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
    obj1 = _make_obj(1)
    obj2 = _make_obj(2)
    obj3 = _make_dropped_obj(3)

    def fake_record(obj, fout, drops):
        if not obj.is_area():
            return 0
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

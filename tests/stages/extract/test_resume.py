"""Resume / WAL behavior tests (split from test_extract.py)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from osm_polygon_selection.stages.extract import extract

from ._helpers import _make_dropped_obj, _make_obj, _read_jsonl_rows


def test_resume_skips_already_seen_kept_ids(tmp_path: Path) -> None:
    out = tmp_path / "out.jsonl"
    wal = out.with_suffix(out.suffix + ".seen_ids")
    out.parent.mkdir(parents=True, exist_ok=True)
    wal.write_text("42\n")

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
    out = tmp_path / "out.jsonl"
    wal = out.with_suffix(out.suffix + ".seen_ids")
    out.parent.mkdir(parents=True, exist_ok=True)
    wal.write_text("99\n")
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
    rows = _read_jsonl_rows(out)
    assert [r["id"] for r in rows] == [100]
    log_data = json.loads(out.with_suffix(out.suffix + ".run.json").read_text())
    assert log_data["polygons_written"] == 1
    assert log_data["polygons_skipped_resume"] == 1
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

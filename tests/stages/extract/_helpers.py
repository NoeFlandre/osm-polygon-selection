"""Shared helpers for extract-stage tests."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from osm_polygon_selection.stages.extract import extract


def _make_obj(osm_id: int) -> MagicMock:
    obj = MagicMock()
    obj.id = osm_id
    obj.is_area.return_value = True
    return obj


def _make_dropped_obj(osm_id: int) -> MagicMock:
    obj = MagicMock()
    obj.id = osm_id
    obj.is_area.return_value = False
    return obj


def _drive(
    tmp_path: Path,
    mock_objects: list[MagicMock],
    limit: int | None = None,
    pbf_name: str = "fake.osm.pbf",
):
    pbf = tmp_path / pbf_name
    pbf.touch()
    out = tmp_path / "out.jsonl"

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

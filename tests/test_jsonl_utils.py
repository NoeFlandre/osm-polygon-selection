"""Tests for shared JSONL streaming helper."""

import json
from pathlib import Path

from osm_polygon_selection.jsonl_utils import stream_jsonl


def _write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def _read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def test_stream_jsonl_writes_kept_rows(tmp_path: Path) -> None:
    in_p = tmp_path / "in.jsonl"
    out_p = tmp_path / "out.jsonl"
    _write_rows(in_p, [{"id": 1}, {"id": 2}, {"id": 3}])

    kept, seen = stream_jsonl(in_p, out_p, lambda r: r)

    assert kept == 3
    assert seen == 3
    assert _read_rows(out_p) == [{"id": 1}, {"id": 2}, {"id": 3}]


def test_stream_jsonl_drops_rows_returning_none(tmp_path: Path) -> None:
    in_p = tmp_path / "in.jsonl"
    out_p = tmp_path / "out.jsonl"
    _write_rows(in_p, [{"id": 1}, {"id": 2}, {"id": 3}])

    def keep_even(r: dict) -> dict | None:
        return r if r["id"] % 2 == 0 else None

    kept, seen = stream_jsonl(in_p, out_p, keep_even)

    assert kept == 1
    assert seen == 3
    assert _read_rows(out_p) == [{"id": 2}]


def test_stream_jsonl_transforms_rows(tmp_path: Path) -> None:
    in_p = tmp_path / "in.jsonl"
    out_p = tmp_path / "out.jsonl"
    _write_rows(in_p, [{"id": 1, "tags": ["a"]}, {"id": 2, "tags": ["b"]}])

    def add_field(r: dict) -> dict:
        r["processed"] = True
        return r

    stream_jsonl(in_p, out_p, add_field)
    rows = _read_rows(out_p)
    assert all(r["processed"] is True for r in rows)


def test_stream_jsonl_creates_output_parent_dir(tmp_path: Path) -> None:
    in_p = tmp_path / "in.jsonl"
    out_p = tmp_path / "deep" / "nested" / "out.jsonl"
    _write_rows(in_p, [{"id": 1}])

    stream_jsonl(in_p, out_p, lambda r: r)

    assert out_p.exists()


def test_stream_jsonl_empty_input(tmp_path: Path) -> None:
    in_p = tmp_path / "in.jsonl"
    out_p = tmp_path / "out.jsonl"
    in_p.write_text("")

    kept, seen = stream_jsonl(in_p, out_p, lambda r: r)

    assert kept == 0
    assert seen == 0
    assert out_p.exists()
    assert out_p.read_text() == ""


def test_stream_jsonl_handles_missing_optional_fields(tmp_path: Path) -> None:
    """Transforms that read fields not present in some rows should drop them."""
    in_p = tmp_path / "in.jsonl"
    out_p = tmp_path / "out.jsonl"
    _write_rows(in_p, [{"id": 1}, {"id": 2, "extra": "x"}])

    def only_with_extra(r: dict) -> dict | None:
        return r if "extra" in r else None

    kept, seen = stream_jsonl(in_p, out_p, only_with_extra)

    assert kept == 1
    assert seen == 2
    assert _read_rows(out_p) == [{"id": 2, "extra": "x"}]

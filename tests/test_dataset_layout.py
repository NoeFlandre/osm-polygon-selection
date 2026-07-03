"""Tests for osm_polygon_selection.dataset_layout.

TDD red phase: written before src/osm_polygon_selection/dataset_layout.py.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from osm_polygon_selection.dataset_layout import (
    cleanup_loose_root_files,
    ensure_layout,
    human_size,
    move_combined,
    move_country_files,
    move_preview,
    move_sample,
)


class TestEnsureLayout:
    def test_creates_required_subfolders(self, tmp_path: Path) -> None:
        ensure_layout(tmp_path)
        for sub in ("per_country", "combined", "sample", "preview"):
            assert (tmp_path / sub).is_dir()

    def test_idempotent(self, tmp_path: Path) -> None:
        ensure_layout(tmp_path)
        ensure_layout(tmp_path)  # second call no-op
        for sub in ("per_country", "combined", "sample", "preview"):
            assert (tmp_path / sub).is_dir()


class TestMoveCountryFiles:
    def test_moves_parquets_into_subfolders(self, tmp_path: Path) -> None:
        ensure_layout(tmp_path)
        # Simulate a built dataset: flat per-country parquets at root
        for c in ("albania", "andorra", "italy"):
            (tmp_path / f"{c}.parquet").touch()
        moved = move_country_files(tmp_path, ["albania", "andorra", "italy"])
        assert moved == 3
        for c in ("albania", "andorra", "italy"):
            assert (tmp_path / "per_country" / c / f"{c}.parquet").exists()
            assert not (tmp_path / f"{c}.parquet").exists()

    def test_skips_missing_country(self, tmp_path: Path) -> None:
        ensure_layout(tmp_path)
        moved = move_country_files(tmp_path, ["ghost"])
        assert moved == 0


class TestMoveCombined:
    def test_moves_all_world_parquet(self, tmp_path: Path) -> None:
        ensure_layout(tmp_path)
        (tmp_path / "all_world.parquet").touch()
        assert move_combined(tmp_path) is True
        assert (tmp_path / "combined" / "all_world.parquet").exists()

    def test_returns_false_when_missing(self, tmp_path: Path) -> None:
        ensure_layout(tmp_path)
        assert move_combined(tmp_path) is False


class TestMoveSample:
    def test_copies_sample(self, tmp_path: Path) -> None:
        ensure_layout(tmp_path)
        src = tmp_path / "src_sample.jsonl"
        src.write_text("{}\n")
        assert move_sample(tmp_path, src) is True
        assert (tmp_path / "sample" / "sample_map.jsonl").exists()


class TestMovePreview:
    def test_copies_preview(self, tmp_path: Path) -> None:
        ensure_layout(tmp_path)
        src = tmp_path / "src_map.png"
        src.write_bytes(b"\x89PNG\r\n\x1a\n")
        assert move_preview(tmp_path, src) is True
        assert (tmp_path / "preview" / "map_preview.png").exists()


class TestCleanupLooseRootFiles:
    def test_deletes_loose_parquets(self, tmp_path: Path) -> None:
        ensure_layout(tmp_path)
        for c in ("albania", "andorra"):
            (tmp_path / f"{c}.parquet").touch()
            (tmp_path / "per_country" / c).mkdir(parents=True, exist_ok=True)
        deleted = cleanup_loose_root_files(tmp_path)
        assert deleted == 2
        for c in ("albania", "andorra"):
            assert not (tmp_path / f"{c}.parquet").exists()

    def test_does_not_delete_kept_files(self, tmp_path: Path) -> None:
        ensure_layout(tmp_path)
        (tmp_path / "README.md").touch()
        (tmp_path / "manifest.json").touch()
        (tmp_path / "metadata.yaml").touch()
        deleted = cleanup_loose_root_files(tmp_path)
        assert deleted == 0
        assert (tmp_path / "README.md").exists()
        assert (tmp_path / "manifest.json").exists()
        assert (tmp_path / "metadata.yaml").exists()


class TestHumanSize:
    def test_bytes(self) -> None:
        assert human_size(500) == "500 B"

    def test_kb(self) -> None:
        out = human_size(2048)
        assert "KB" in out

    def test_mb(self) -> None:
        out = human_size(2 * 1024 * 1024)
        assert "MB" in out

    def test_gb(self) -> None:
        out = human_size(3 * 1024 * 1024 * 1024)
        assert "GB" in out

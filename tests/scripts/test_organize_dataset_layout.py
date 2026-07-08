"""Tests for `scripts/organize_dataset.py::main` against a minimal temp root.

These pin the contract that the layout pass works on a freshly-created
empty directory (no pre-existing subfolders). In particular the
`write_folder_readmes` step writes a `splits/README.md`, so `splits/`
must exist by then.
"""

from __future__ import annotations

import json
from pathlib import Path


def _build_minimal_dataset_root(root: Path) -> None:
    """Lay down the minimum files `organize_dataset.main` expects."""
    root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "version": "v0.0.0",
        "git_sha": "abc1234",
        "built_at": "2026-01-01T00:00:00",
        "total_polygons": 0,
        "n_countries": 0,
        "countries": [],
        "schema": ["osm_id"],
        "filters": {"min_area_km2": 0.1, "max_area_km2": 100.0, "whitelist_size": 22075},
    }
    (root / "manifest.json").write_text(json.dumps(manifest))


def test_main_creates_splits_directory(tmp_path: Path) -> None:
    """main() must create the splits/ directory before writing splits/README.md.

    Regression: SUBFOLDERS used to omit "splits" so write_folder_readmes
    crashed with FileNotFoundError on a fresh root.
    """
    from scripts.organize_dataset import main as organize_main

    _build_minimal_dataset_root(tmp_path)

    # Run with no sample/preview sources (they are optional).
    summary = organize_main(root=tmp_path)

    assert (tmp_path / "splits").is_dir()
    assert (tmp_path / "splits" / "README.md").is_file()
    # ensure_layout ran:
    assert "ensure_layout" in summary["steps"]
    # Folder READMEs (incl splits) were written:
    assert summary.get("folder_readmes_written", 0) >= 1


def test_main_works_on_empty_root(tmp_path: Path) -> None:
    """main() must not raise on a freshly-created dataset root with no subfolders."""
    from scripts.organize_dataset import main as organize_main

    _build_minimal_dataset_root(tmp_path)

    # Should not raise.
    organize_main(root=tmp_path)

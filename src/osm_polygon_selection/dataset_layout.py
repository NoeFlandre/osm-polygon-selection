"""Dataset directory layout helpers.

Public-facing layout is::

    dataset/
    ├── README.md, manifest.json, metadata.yaml       (root landing page)
    ├── per_country/<country>/{<country>.parquet, README.md}
    ├── combined/{all_europe.parquet, README.md}
    ├── sample/{sample_map.jsonl, README.md}
    ├── preview/{map_preview.png, README.md}
    └── splits/{split_manifest.json}

These helpers create the subfolder skeleton and move/copy files
into it. They are pure file-system operations: no JSON parsing,
no pyarrow, no remote API calls.
"""

from __future__ import annotations

import shutil
from collections.abc import Iterable
from pathlib import Path

# Subfolders every dataset directory must contain.
SUBFOLDERS: tuple[str, ...] = ("per_country", "combined", "sample", "preview")

# Root-level files that should NOT be deleted by cleanup_loose_root_files.
ROOT_KEPT_FILES: frozenset[str] = frozenset(
    {"README.md", "manifest.json", "metadata.yaml"}
)


def ensure_layout(root: Path) -> None:
    """Create the four subfolders under ``root`` (idempotent)."""
    for sub in SUBFOLDERS:
        (root / sub).mkdir(parents=True, exist_ok=True)


def _move_atomic(src: Path, dst: Path) -> bool:
    """Move src -> dst. Returns True if moved, False if src missing."""
    if not src.is_file():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    return True


def move_country_files(root: Path, countries: Iterable[str]) -> int:
    """Move each ``<country>.parquet`` from root to ``per_country/<country>/``.

    Returns the count of successfully moved files.
    """
    moved = 0
    for country in countries:
        if _move_atomic(root / f"{country}.parquet",
                        root / "per_country" / country / f"{country}.parquet"):
            moved += 1
    return moved


def move_combined(root: Path) -> bool:
    """Move ``all_europe.parquet`` from root to ``combined/``."""
    return _move_atomic(root / "all_europe.parquet",
                        root / "combined" / "all_europe.parquet")


def move_sample(root: Path, sample_src: Path) -> bool:
    """Copy ``sample_src`` to ``sample/sample_map.jsonl``."""
    if not sample_src.is_file():
        return False
    dst = root / "sample" / "sample_map.jsonl"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(sample_src, dst)
    return True


def move_preview(root: Path, preview_src: Path) -> bool:
    """Copy ``preview_src`` to ``preview/map_preview.png``."""
    if not preview_src.is_file():
        return False
    dst = root / "preview" / "map_preview.png"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(preview_src, dst)
    return True


def cleanup_loose_root_files(root: Path) -> int:
    """Delete loose ``*.parquet`` files from the dataset root.

    These are leftovers from a flat layout that have been moved
    into subfolders. Root-level non-parquet files (README, manifest,
    metadata) are preserved.

    Returns the number of deleted files.
    """
    deleted = 0
    for p in root.iterdir():
        if p.is_file() and p.suffix == ".parquet":
            p.unlink()
            deleted += 1
    return deleted


def human_size(num_bytes: int) -> str:
    """Format a byte count as a human-readable string (B/KB/MB/GB)."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    if num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.1f} MB"
    return f"{num_bytes / (1024 * 1024 * 1024):.1f} GB"

"""File listing and relative-path set computation for the upload."""

from __future__ import annotations

from pathlib import Path


def list_files(root: Path) -> list[Path]:
    """Return all files under ``root``, sorted by size (smallest first).

    Smallest-first ordering means the small metadata files upload
    first; the user sees the dataset page populated quickly while
    the big combined parquet uploads in the background.
    """
    return sorted(
        [p for p in root.rglob("*") if p.is_file()],
        key=lambda p: p.stat().st_size,
    )


def relative_paths(files: list[Path], root: Path) -> set[str]:
    """Return the set of paths-as-strings relative to ``root``."""
    return {str(p.relative_to(root)) for p in files}


def total_size_bytes(files: list[Path]) -> int:
    """Sum of file sizes in bytes."""
    return sum(p.stat().st_size for p in files)


__all__ = ["list_files", "relative_paths", "total_size_bytes"]

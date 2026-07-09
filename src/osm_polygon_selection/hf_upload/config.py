"""Default configuration for the HF upload pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from osm_polygon_selection.config import RuntimeConfig


DEFAULT_REPO_ID = "NoeFlandre/osm-polygon-selection"
DEFAULT_ROOT = RuntimeConfig.from_env().dataset_root

# Ignore patterns used by ``upload_folder``. Cheap to keep, expensive
# if missing (a stray ``.DS_Store`` or .pyc would upload).
DEFAULT_IGNORE_PATTERNS: list[str] = [
    "*.tmp",
    "*.wal",
    "*.pyc",
    "__pycache__/*",
    ".DS_Store",
]

# How many deletes to bundle into a single HF commit during cleanup.
DELETE_CHUNK_SIZE = 100


@dataclass(frozen=True)
class UploadConfig:
    """Inputs for :func:`osm_polygon_selection.hf_upload.runner.run`."""

    root: Path
    repo_id: str
    commit_message: str = "Update dataset"
    dry_run: bool = False
    skip_cleanup: bool = False
    ignore_patterns: list[str] = field(default_factory=lambda: list(DEFAULT_IGNORE_PATTERNS))
    delete_chunk_size: int = DELETE_CHUNK_SIZE


__all__ = [
    "DEFAULT_IGNORE_PATTERNS",
    "DEFAULT_REPO_ID",
    "DEFAULT_ROOT",
    "DELETE_CHUNK_SIZE",
    "UploadConfig",
]

"""Top-level orchestration for the HF upload pipeline.

Three steps (mirrors the original ``scripts/upload_to_hf.py``):

1. List local files (sorted by size, smallest first).
2. Compute + print dry-run output if requested.
3. Delete stale remote files (unless ``--skip-cleanup``).
4. ``upload_folder`` in a single commit.
"""

from __future__ import annotations

from huggingface_hub import HfApi

from osm_polygon_selection.hf_upload.cleanup import delete_stale, hf_files
from osm_polygon_selection.hf_upload.config import UploadConfig
from osm_polygon_selection.hf_upload.files import (
    list_files,
    relative_paths,
    total_size_bytes,
)
from osm_polygon_selection.hf_upload.token import get_token


def run(config: UploadConfig) -> int:
    """Run the upload pipeline according to ``config``. Returns exit code."""
    api = HfApi(token=get_token())
    files = list_files(config.root)
    n_files = len(files)
    total_bytes = total_size_bytes(files)
    print(f"root: {config.root}")
    print(f"repo: {config.repo_id}")
    print(f"local files: {n_files} ({total_bytes / 1e9:.2f} GB total)")

    local_rel = relative_paths(files, config.root)

    if config.dry_run:
        for p in files:
            size_mb = p.stat().st_size / 1_048_576
            rel = p.relative_to(config.root)
            print(f"  {size_mb:>10.1f} MB  {rel}")
        stale = sorted(hf_files(api, config.repo_id) - local_rel)
        if stale:
            print(f"\nstale files on HF (would be deleted): {len(stale)}")
            for s in stale[:30]:
                print(f"  - {s}")
            if len(stale) > 30:
                print(f"  ... and {len(stale) - 30} more")
        return 0

    n_deleted = 0
    if not config.skip_cleanup:
        n_deleted = delete_stale(
            api,
            repo_id=config.repo_id,
            local_files=local_rel,
            commit_message=config.commit_message,
            chunk_size=config.delete_chunk_size,
        )
        print(f"deleted {n_deleted} stale files")

    print(f"uploading {n_files} files in 1 commit...", flush=True)
    api.upload_folder(
        folder_path=str(config.root),
        repo_id=config.repo_id,
        repo_type="dataset",
        commit_message=config.commit_message,
        ignore_patterns=config.ignore_patterns,
    )
    print(f"done: {n_files} files uploaded, {n_deleted} stale deleted")
    return 0


__all__ = ["run"]

"""Upload the reorganized dataset to HuggingFace.

Mirrors ``dataset/`` to the NoeFlandre/osm-polygon-selection repo.

The script first reconciles the HF repo with the local state:
any files that exist on HF but not locally are deleted (so
stale files from earlier per-country uploads at the repo root
get cleaned up). Then it does a single ``upload_folder`` commit
for the rest. ``upload_folder`` batches all file uploads into
a single commit, which sidesteps the HF per-commit rate limit
(128 commits/hour).

The combined parquet is uploaded last (it's the largest single
file at ~13GB compressed). If the upload is interrupted, the
per-country parquets are already in place and the dataset is
usable from there.

The script uses the HF_TOKEN environment variable, or falls back
to the cached token at ~/.cache/huggingface/token. No token is
ever printed or logged.

Usage:
    uv run scripts/upload_to_hf.py [--root PATH] [--repo-id ID]
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from huggingface_hub import CommitOperationDelete, HfApi


DEFAULT_REPO_ID = "NoeFlandre/osm-polygon-selection"
DEFAULT_ROOT = Path("/Volumes/Seagate M3/osm-polygon-selection/dataset")


def _get_token() -> str:
    token = os.environ.get("HF_TOKEN")
    if token:
        return token
    cached = Path.home() / ".cache" / "huggingface" / "token"
    if cached.is_file():
        return cached.read_text().strip()
    raise SystemExit("no HF token found; set HF_TOKEN env var")


def _list_files(root: Path) -> list[Path]:
    """Return all files under root, sorted by size (smallest first).

    Smallest-first ordering means the small metadata files upload
    first; the user sees the dataset page populated quickly while
    the big combined parquet uploads in the background.
    """
    return sorted(
        [p for p in root.rglob("*") if p.is_file()],
        key=lambda p: p.stat().st_size,
    )


def _hf_files(api: HfApi, repo_id: str) -> set[str]:
    """Return the set of file paths currently on HF for the dataset."""
    try:
        items = api.list_repo_files(repo_id=repo_id, repo_type="dataset")
    except Exception:
        return set()
    return set(items)


def _delete_stale(
    api: HfApi, repo_id: str, local_files: set[str], commit_message: str
) -> int:
    """Delete HF files that don't exist locally. Returns count deleted.

    Important to call this BEFORE the bulk upload so the deleted
    files don't end up re-uploaded on a retry. Returns 0 if
    nothing to delete.
    """
    hf_files = _hf_files(api, repo_id)
    stale = sorted(hf_files - local_files)
    if not stale:
        return 0
    print(f"deleting {len(stale)} stale files from HF...", flush=True)
    # delete_files takes a single commit; group into chunks of
    # 100 to keep individual commit sizes manageable.
    for i in range(0, len(stale), 100):
        chunk = stale[i : i + 100]
        from huggingface_hub import CommitOperationDelete
        operations = [
            CommitOperationDelete(path_in_repo=p) for p in chunk
        ]
        api.create_commit(
            repo_id=repo_id,
            repo_type="dataset",
            operations=operations,
            commit_message=f"{commit_message} (cleanup {i+1}-{i+len(chunk)})",
        )
    return len(stale)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="List files that would be uploaded without uploading",
    )
    parser.add_argument(
        "--commit-message", default="Update dataset",
        help="Single commit message for the entire folder upload",
    )
    parser.add_argument(
        "--skip-cleanup", action="store_true",
        help="Don't delete stale files from HF before uploading",
    )
    args = parser.parse_args()

    api = HfApi(token=_get_token())
    files = _list_files(args.root)
    total_bytes = sum(p.stat().st_size for p in files)
    print(f"root: {args.root}")
    print(f"repo: {args.repo_id}")
    print(f"local files: {len(files)} ({total_bytes / 1e9:.2f} GB total)")

    local_rel = {str(p.relative_to(args.root)) for p in files}

    if args.dry_run:
        for p in files:
            size_mb = p.stat().st_size / 1_048_576
            rel = p.relative_to(args.root)
            print(f"  {size_mb:>10.1f} MB  {rel}")
        hf_files = _hf_files(api, args.repo_id)
        stale = sorted(hf_files - local_rel)
        if stale:
            print(f"\nstale files on HF (would be deleted): {len(stale)}")
            for s in stale[:30]:
                print(f"  - {s}")
            if len(stale) > 30:
                print(f"  ... and {len(stale) - 30} more")
        return 0

    # Step 1: delete stale files from HF (e.g. all_europe.parquet,
    # per-country parquets left over from the old "upload files
    # individually" code path that wrote them to the repo root).
    n_deleted = 0
    if not args.skip_cleanup:
        n_deleted = _delete_stale(api, args.repo_id, local_rel, args.commit_message)
        print(f"deleted {n_deleted} stale files")

    # Step 2: batch upload in a single commit.
    print(f"uploading {len(files)} files in 1 commit...", flush=True)
    api.upload_folder(
        folder_path=str(args.root),
        repo_id=args.repo_id,
        repo_type="dataset",
        commit_message=args.commit_message,
        ignore_patterns=[
            "*.tmp", "*.wal", "*.pyc", "__pycache__/*",
            ".DS_Store",
        ],
    )
    print(f"done: {len(files)} files uploaded, {n_deleted} stale deleted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

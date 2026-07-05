"""Upload the reorganized dataset to HuggingFace.

Mirrors ``dataset/`` to the NoeFlandre/osm-polygon-selection repo.
Files are added in order: README, manifest, metadata, splits,
per-country parquets, combined parquet, sample, preview.

The combined parquet is uploaded last (it's the largest single
file at ~6GB compressed). If the upload is interrupted, the
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

from huggingface_hub import HfApi


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
    args = parser.parse_args()

    api = HfApi(token=_get_token())
    files = _list_files(args.root)
    total_bytes = sum(p.stat().st_size for p in files)
    print(f"root: {args.root}")
    print(f"repo: {args.repo_id}")
    print(f"files: {len(files)} ({total_bytes / 1e9:.2f} GB total)")

    if args.dry_run:
        for p in files:
            size_mb = p.stat().st_size / 1_048_576
            rel = p.relative_to(args.root)
            print(f"  {size_mb:>10.1f} MB  {rel}")
        return 0

    # Batch upload: a single commit for the whole folder, instead
    # of one commit per file (which the HF commit API rate-limits
    # at 128/hour). upload_folder handles multi-GB directories
    # internally with chunked resumable uploads, so a ~14 GB
    # dataset fits in a single commit.
    print(f"uploading {len(files)} files in 1 commit...", flush=True)
    api.upload_folder(
        folder_path=str(args.root),
        repo_id=args.repo_id,
        repo_type="dataset",
        commit_message=args.commit_message,
        ignore_patterns=["*.tmp", "*.wal", "*.pyc", "__pycache__/*"],
    )
    print(f"done: {len(files)} files uploaded to {args.repo_id} (1 commit)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

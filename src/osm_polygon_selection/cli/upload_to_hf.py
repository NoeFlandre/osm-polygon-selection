"""Upload-to-HuggingFace CLI.

Thin wrapper around :mod:`osm_polygon_selection.hf_upload.runner`.

The public CLI surface (preserved for backwards-compat):

- ``--root PATH`` (default: ``RuntimeConfig.dataset_root``)
- ``--repo-id ID`` (default: ``NoeFlandre/osm-polygon-selection``)
- ``--commit-message TEXT`` (default: ``"Update dataset"``)
- ``--dry-run``
- ``--skip-cleanup``

Legacy positional ``dataset_dir`` is no longer required (the
default is provided by ``--root``).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from osm_polygon_selection.hf_upload.config import (
    DEFAULT_IGNORE_PATTERNS,
    DEFAULT_REPO_ID,
    DEFAULT_ROOT,
    UploadConfig,
)
from osm_polygon_selection.hf_upload.runner import run as _hf_run


def upload_to_hf(
    dataset_dir: Path,
    repo_id: str = DEFAULT_REPO_ID,
    dry_run: bool = False,
    cleanup: bool = True,
    commit_message: str = "Update dataset",
    delete_chunk_size: int = 50,
) -> int:
    """Public entry point used by tests + the script wrapper."""
    config = UploadConfig(
        root=dataset_dir,
        repo_id=repo_id,
        dry_run=dry_run,
        skip_cleanup=not cleanup,
        commit_message=commit_message,
        ignore_patterns=DEFAULT_IGNORE_PATTERNS,
        delete_chunk_size=delete_chunk_size,
    )
    return _hf_run(config)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=DEFAULT_ROOT,
        help="Local dataset directory to upload (default: RuntimeConfig.dataset_root)",
    )
    parser.add_argument(
        "--repo-id", dest="repo_id", type=str,
        default=DEFAULT_REPO_ID,
        help=f"HuggingFace repo id (default: {DEFAULT_REPO_ID})",
    )
    parser.add_argument(
        "--commit-message", dest="commit_message", type=str,
        default="Update dataset",
        help='HF commit message (default: "Update dataset")',
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Compute stale/added file lists but do not call HF API",
    )
    parser.add_argument(
        "--skip-cleanup", dest="skip_cleanup", action="store_true",
        help="Skip the delete-stale step after upload",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return upload_to_hf(
        dataset_dir=args.root,
        repo_id=args.repo_id,
        dry_run=args.dry_run,
        cleanup=not args.skip_cleanup,
        commit_message=args.commit_message,
    )


if __name__ == "__main__":
    raise SystemExit(main())

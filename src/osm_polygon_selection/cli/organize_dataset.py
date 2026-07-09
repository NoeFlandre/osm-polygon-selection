"""Organize-dataset CLI: move/rename files into the canonical layout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from osm_polygon_selection.dataset_organize import run_organize
from osm_polygon_selection.dataset_organize.runner import (
    DEFAULT_PREVIEW_SRC,
    DEFAULT_ROOT,
    DEFAULT_SAMPLE_SRC,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--sample-src", type=Path, default=DEFAULT_SAMPLE_SRC)
    parser.add_argument("--preview-src", type=Path, default=DEFAULT_PREVIEW_SRC)
    return parser


def main(
    root: Optional[Path] = None,
    sample_src: Optional[Path] = None,
    preview_src: Optional[Path] = None,
) -> dict:
    """CLI entry: parses argv if no kwargs provided, else runs directly."""
    if root is None or sample_src is None or preview_src is None:
        import sys as _sys
        # Pass sys.argv[1:] only when we have a TTY (avoid pytest's argv).
        if _sys.argv and _sys.argv[0].endswith("organize_dataset.py"):
            args = build_parser().parse_args(_sys.argv[1:])
        else:
            args = build_parser().parse_args([])
        root = root or args.root
        sample_src = sample_src or args.sample_src
        preview_src = preview_src or args.preview_src
    if isinstance(root, str):
        root = Path(root)
    if isinstance(sample_src, str):
        sample_src = Path(sample_src)
    if isinstance(preview_src, str):
        preview_src = Path(preview_src)
    summary = run_organize(
        root=root,
        sample_src=sample_src,
        preview_src=preview_src,
    )
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    main()

"""CLI smoke test for ``scripts/upload_to_hf.py``.

Domain behavior is covered by ``tests/hf_upload/test_hf_upload_package.py``.
This file pins CLI delegation + argparse help.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
UPLOAD = SCRIPTS_DIR / "upload_to_hf.py"


def test_cli_help_runs() -> None:
    result = subprocess.run(
        [sys.executable, str(UPLOAD), "--help"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    # The original public CLI surface is preserved (backwards-compat):
    assert "--root" in result.stdout
    assert "--repo-id" in result.stdout
    assert "--commit-message" in result.stdout
    assert "--dry-run" in result.stdout
    assert "--skip-cleanup" in result.stdout


def test_parser_parses_no_positional_args() -> None:
    """``build_parser`` with no positional should yield the default root."""
    from osm_polygon_selection.cli.upload_to_hf import build_parser
    args = build_parser().parse_args([])
    # The default is DEFAULT_ROOT from RuntimeConfig, but root
    # should at least be settable to a Path-like.
    assert args.root is not None
    # --root / --repo-id / --commit-message are flags, not positionals.
    assert hasattr(args, "root")
    assert hasattr(args, "repo_id")
    assert hasattr(args, "commit_message")
    assert args.skip_cleanup is False
    assert args.dry_run is False


def test_parser_parses_root_override(tmp_path: Path) -> None:
    from osm_polygon_selection.cli.upload_to_hf import build_parser
    args = build_parser().parse_args(["--root", str(tmp_path)])
    assert str(args.root) == str(tmp_path)


def test_parser_parses_commit_message() -> None:
    from osm_polygon_selection.cli.upload_to_hf import build_parser
    args = build_parser().parse_args(["--commit-message", "Update dataset"])
    assert args.commit_message == "Update dataset"


def test_parser_parses_skip_cleanup() -> None:
    from osm_polygon_selection.cli.upload_to_hf import build_parser
    args = build_parser().parse_args(["--skip-cleanup"])
    assert args.skip_cleanup is True

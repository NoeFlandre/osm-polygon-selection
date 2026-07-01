"""Git metadata helpers for the build/publish pipeline.

Three tiny pure-ish functions used by README writers to record
provenance (current commit SHA, repo root). All functions are
defensive: if git is missing or the directory isn't a repo, they
fall back to "unknown" / "." without raising.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# The project root is the directory that contains pyproject.toml.
# Hard-coded for the canonical repo; callers can override via the
# optional `cwd` parameter on each function.
_DEFAULT_REPO_ROOT = Path("/Users/noeflandre/osm-polygon-selection")


def _run_git(args: list[str], cwd: Path | None) -> str:
    """Run a git command and return stripped stdout, or '' on error."""
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            cwd=str(cwd) if cwd else None,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def repo_root(cwd: Path | None = None) -> Path:
    """Return the repo root Path, falling back to a sensible default.

    Uses ``git rev-parse --show-toplevel`` when possible. If git is
    missing or we're not in a repo, returns ``_DEFAULT_REPO_ROOT`` if
    it exists, else ``Path('.')``.
    """
    out = _run_git(["rev-parse", "--show-toplevel"], cwd)
    if out:
        return Path(out)
    if _DEFAULT_REPO_ROOT.exists():
        return _DEFAULT_REPO_ROOT
    return Path(".")


def git_short_sha(cwd: Path | None = None) -> str:
    """Return the 7-char short SHA of HEAD, or 'unknown' on error."""
    sha = _run_git(["rev-parse", "--short", "HEAD"], cwd)
    return sha or "unknown"


def git_sha(cwd: Path | None = None) -> str:
    """Return the full SHA of HEAD, or 'unknown' on error."""
    sha = _run_git(["rev-parse", "HEAD"], cwd)
    return sha or "unknown"

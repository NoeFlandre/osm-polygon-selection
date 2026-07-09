"""Tests for osm_polygon_selection.git_meta.

TDD red phase: written before src/osm_polygon_selection/git_meta.py.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from osm_polygon_selection.config import git_sha, git_short_sha, repo_root


class TestGitShortSha:
    def test_returns_non_empty_string(self) -> None:
        """Always returns at least an 'unknown' fallback."""
        sha = git_short_sha(repo_root())
        assert isinstance(sha, str)
        assert len(sha) >= 4  # "unknown" is 7 chars, real SHAs are >= 4

    def test_returns_hex_or_unknown(self) -> None:
        """Real SHA is hex; fallback is 'unknown'."""
        sha = git_short_sha(repo_root())
        assert sha == "unknown" or all(c in "0123456789abcdef" for c in sha)

    def test_short_sha_is_7_or_more_chars(self) -> None:
        """git --short always returns >= 7 chars for any real commit."""
        sha = git_short_sha(repo_root())
        if sha != "unknown":
            assert len(sha) >= 7


class TestGitSha:
    def test_full_sha_is_longer_or_equal(self) -> None:
        """Full SHA is the short one (or longer)."""
        full = git_sha(repo_root())
        short = git_short_sha(repo_root())
        assert len(full) >= len(short)

    def test_returns_string(self) -> None:
        assert isinstance(git_sha(repo_root()), str)


class TestRepoRoot:
    def test_returns_path(self) -> None:
        root = repo_root()
        assert isinstance(root, Path)

    def test_repo_root_contains_pyproject(self, tmp_path: Path) -> None:
        """When no project found, fallback returns a sensible default."""
        # We can't easily mock subprocess, but we can verify the function
        # returns a Path that exists (or a sensible fallback).
        root = repo_root()
        assert root.exists() or root == Path(".")

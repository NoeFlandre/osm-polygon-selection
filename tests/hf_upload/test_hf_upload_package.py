"""Package-level tests for ``osm_polygon_selection.hf_upload``.

Covers the public surface split out of ``scripts/upload_to_hf.py``:

- token resolution order (env -> cache -> SystemExit)
- file listing sorted by size ascending
- relative-path set
- stale HF file computation
- dry-run does not call upload/delete
- cleanup chunks stale deletes by 100
- ``--skip-cleanup`` skips deletion
- upload uses ignore patterns

All HF calls are mocked via a fake ``HfApi``; no network.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from osm_polygon_selection.hf_upload import (
    DEFAULT_IGNORE_PATTERNS,
    DEFAULT_REPO_ID,
    UploadConfig,
    run,
)
from osm_polygon_selection.hf_upload.cleanup import (
    compute_stale,
    delete_stale,
    hf_files,
)
from osm_polygon_selection.hf_upload.config import DELETE_CHUNK_SIZE
from osm_polygon_selection.hf_upload.files import (
    list_files,
    relative_paths,
    total_size_bytes,
)
from osm_polygon_selection.hf_upload.token import get_token


class FakeHfApi:
    """Minimal fake huggingface_hub.HfApi for tests."""

    def __init__(self, remote_files: list[str] | None = None) -> None:
        self.remote_files = list(remote_files or [])
        self.uploads: list[dict[str, Any]] = []
        self.commits: list[dict[str, Any]] = []
        self.list_calls = 0
        self.upload_folder_calls = 0

    def list_repo_files(self, *, repo_id: str, repo_type: str) -> list[str]:
        self.list_calls += 1
        return list(self.remote_files)

    def create_commit(
        self,
        *,
        repo_id: str,
        repo_type: str,
        operations: list[Any],
        commit_message: str,
    ) -> Any:
        self.commits.append({
            "repo_id": repo_id,
            "operations": operations,
            "message": commit_message,
        })
        return None

    def upload_folder(self, **kwargs: Any) -> Any:
        self.upload_folder_calls += 1
        self.uploads.append(kwargs)


class TestTokenResolution:
    def test_hf_token_env_wins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HF_TOKEN", "from-env")
        monkeypatch.setattr(
            "pathlib.Path.home",
            lambda: Path("/nonexistent"),
        )
        assert get_token() == "from-env"

    def test_cached_token_fallback(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.delenv("HF_TOKEN", raising=False)
        cached = tmp_path / ".cache" / "huggingface" / "token"
        cached.parent.mkdir(parents=True)
        cached.write_text("from-cache")
        monkeypatch.setattr(
            "pathlib.Path.home",
            lambda: tmp_path,
        )
        assert get_token() == "from-cache"

    def test_missing_token_raises_systemexit(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.delenv("HF_TOKEN", raising=False)
        monkeypatch.setattr(
            "pathlib.Path.home",
            lambda: tmp_path,
        )
        with pytest.raises(SystemExit):
            get_token()


class TestListFiles:
    def test_sorted_by_size_ascending(self, tmp_path: Path) -> None:
        (tmp_path / "small").write_text("a")           # 1 byte
        (tmp_path / "medium").write_text("a" * 100)     # 100 bytes
        (tmp_path / "large").write_text("a" * 1000)     # 1000 bytes
        files = list_files(tmp_path)
        assert [p.name for p in files] == ["small", "medium", "large"]

    def test_total_size_bytes(self, tmp_path: Path) -> None:
        (tmp_path / "a").write_text("hello")
        (tmp_path / "b").write_text("world!")
        assert total_size_bytes(list_files(tmp_path)) == 11

    def test_relative_paths(self, tmp_path: Path) -> None:
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "a.txt").write_text("a")
        files = list_files(tmp_path)
        rel = relative_paths(files, tmp_path)
        assert rel == {"sub/a.txt"}


class TestComputeStale:
    def test_stale_is_hf_minus_local(self) -> None:
        assert compute_stale(
            ["a.txt", "b.txt"],
            ["a.txt", "b.txt", "c.txt"],
        ) == ["c.txt"]

    def test_no_stale_when_all_present(self) -> None:
        assert compute_stale(["a", "b"], ["a", "b"]) == []

    def test_empty_inputs(self) -> None:
        assert compute_stale([], []) == []
        assert compute_stale(["a"], []) == []
        assert compute_stale([], ["a"]) == ["a"]


class TestHfFiles:
    def test_returns_set_on_success(self) -> None:
        api = FakeHfApi(remote_files=["a.txt", "b.txt"])
        assert hf_files(api, "any/repo") == {"a.txt", "b.txt"}

    def test_returns_empty_set_on_error(self) -> None:
        class BoomApi:
            def list_repo_files(self, *, repo_id: str, repo_type: str) -> list[str]:
                raise RuntimeError("network down")
        assert hf_files(BoomApi(), "any/repo") == set()


class TestDeleteStale:
    def test_chunks_by_default(self) -> None:
        api = FakeHfApi(remote_files=[f"f{i}" for i in range(250)])
        local = set()
        n = delete_stale(
            api, repo_id="r", local_files=local,
            commit_message="cleanup", chunk_size=100,
        )
        assert n == 250
        # 250 stale / 100 chunk = 3 commits (100, 100, 50).
        assert len(api.commits) == 3
        sizes = [len(c["operations"]) for c in api.commits]
        assert sizes == [100, 100, 50]

    def test_zero_commits_when_no_stale(self) -> None:
        api = FakeHfApi(remote_files=["a", "b"])
        n = delete_stale(
            api, repo_id="r", local_files={"a", "b"},
            commit_message="cleanup", chunk_size=100,
        )
        assert n == 0
        assert api.commits == []


class TestRun:
    def test_dry_run_does_not_upload_or_delete(self, monkeypatch, tmp_path: Path) -> None:
        """Dry-run must call list_files but never upload_folder or delete."""
        # Build a minimal dataset.
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        api = FakeHfApi(remote_files=["a.txt", "stale.txt"])

        monkeypatch.setattr(
            "osm_polygon_selection.hf_upload.runner.get_token",
            lambda: "fake-token",
        )

        # Patch HfApi to return our fake.
        from osm_polygon_selection.hf_upload import runner as runner_mod

        def _fake_hfapi(*, token: str) -> FakeHfApi:
            return api
        monkeypatch.setattr(runner_mod, "HfApi", _fake_hfapi)

        config = UploadConfig(
            root=tmp_path, repo_id="r", dry_run=True,
        )
        rc = run(config)
        assert rc == 0
        assert api.upload_folder_calls == 0
        assert api.commits == []
        assert api.list_calls >= 1

    def test_skip_cleanup_skips_delete(self, monkeypatch, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("a")
        api = FakeHfApi(remote_files=["a.txt", "stale.txt"])

        monkeypatch.setattr(
            "osm_polygon_selection.hf_upload.runner.get_token",
            lambda: "fake-token",
        )
        from osm_polygon_selection.hf_upload import runner as runner_mod
        monkeypatch.setattr(
            runner_mod, "HfApi", lambda *, token: api,
        )

        config = UploadConfig(
            root=tmp_path, repo_id="r",
            dry_run=False, skip_cleanup=True,
        )
        run(config)
        assert api.upload_folder_calls == 1
        assert api.commits == []  # no cleanup

    def test_upload_uses_ignore_patterns(self, monkeypatch, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("a")
        api = FakeHfApi(remote_files=["a.txt"])

        monkeypatch.setattr(
            "osm_polygon_selection.hf_upload.runner.get_token",
            lambda: "fake-token",
        )
        from osm_polygon_selection.hf_upload import runner as runner_mod
        monkeypatch.setattr(
            runner_mod, "HfApi", lambda *, token: api,
        )

        config = UploadConfig(
            root=tmp_path, repo_id="r",
            dry_run=False, skip_cleanup=True,
        )
        run(config)
        assert api.upload_folder_calls == 1
        kwargs = api.uploads[0]
        assert kwargs["ignore_patterns"] == DEFAULT_IGNORE_PATTERNS


class TestDefaults:
    def test_default_repo_id(self) -> None:
        assert DEFAULT_REPO_ID == "NoeFlandre/osm-polygon-selection"

    def test_default_delete_chunk_size(self) -> None:
        assert DELETE_CHUNK_SIZE == 100

    def test_default_ignore_patterns_includes_dsstore(self) -> None:
        assert ".DS_Store" in DEFAULT_IGNORE_PATTERNS

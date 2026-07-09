"""Stale-file detection and deletion against the HF repo.

Pure functions only: ``compute_stale`` returns the sorted list of
files to delete, ``delete_stale`` issues the actual ``create_commit``
calls in chunks. ``hf_files`` reads the current set of files in
the remote repo (returns empty set on any error to keep the
script running in restricted environments).
"""

from __future__ import annotations

from typing import Any, Iterable, Protocol


class HfApiLike(Protocol):
    """Minimal interface from ``huggingface_hub.HfApi`` we need."""

    def list_repo_files(self, *, repo_id: str, repo_type: str) -> list[str]: ...
    def create_commit(
        self,
        *,
        repo_id: str,
        repo_type: str,
        operations: list[Any],
        commit_message: str,
    ) -> Any: ...


def hf_files(api: HfApiLike, repo_id: str) -> set[str]:
    """Return the set of file paths currently on HF for the dataset."""
    try:
        items = api.list_repo_files(repo_id=repo_id, repo_type="dataset")
    except Exception:
        return set()
    return set(items)


def compute_stale(
    local_files: Iterable[str], remote_files: Iterable[str],
) -> list[str]:
    """Return sorted list of files in HF but not local."""
    return sorted(set(remote_files) - set(local_files))


def delete_stale(
    api: HfApiLike,
    *,
    repo_id: str,
    local_files: Iterable[str],
    commit_message: str,
    chunk_size: int = 100,
) -> int:
    """Delete HF files that don't exist locally, in chunks of ``chunk_size``.

    Returns count deleted. Returns 0 if nothing to delete.
    """
    stale = compute_stale(local_files, hf_files(api, repo_id))
    if not stale:
        return 0
    from huggingface_hub import CommitOperationDelete
    operations = [
        CommitOperationDelete(path_in_repo=p) for p in stale
    ]
    for i in range(0, len(operations), chunk_size):
        chunk = operations[i : i + chunk_size]
        api.create_commit(
            repo_id=repo_id,
            repo_type="dataset",
            operations=chunk,
            commit_message=f"{commit_message} (cleanup {i + 1}-{i + len(chunk)})",
        )
    return len(stale)


__all__ = ["compute_stale", "delete_stale", "hf_files"]

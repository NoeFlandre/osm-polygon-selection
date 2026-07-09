"""Consistency tests for public-facing documentation.

Pins against stale references in README.md and the public docs/
subfolder. Internal docs under ``docs/internal/`` and skills are
exempt from these checks because they document the maintainer
workflow.

Forbidden patterns:

- ``/Users/noeflandre/osm-polygon-selection`` — operator-specific
  absolute paths. Public docs should use ``/path/to/...``.
- ``docs/AFRICA_ROLLOUT.md`` — moved to ``docs/internal/AFRICA_ROLLOUT.md``.
- ``all_europe.parquet`` — the dataset's combined parquet has been
  renamed to ``all_world.parquet``.
- ``tests/test_*.py`` — root-level test files were reorganized
  into domain subfolders in an earlier quality-uplift.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Public docs that must not contain any of the forbidden patterns.
PUBLIC_DOCS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs" / "architecture.md",
    REPO_ROOT / "docs" / "PERFORMANCE.md",
    REPO_ROOT / "docs" / "dataset_state.md",
    REPO_ROOT / "docs" / "whitelist_decisions.md",
]

FORBIDDEN = [
    ("/Users/noeflandre/osm-polygon-selection", "absolute operator path"),
    ("/Users/noeflandre", "absolute operator home-directory path"),
    ("docs/AFRICA_ROLLOUT.md", "AFRICA_ROLLOUT moved to docs/internal/"),
    ("all_europe.parquet", "combined parquet renamed to all_world.parquet"),
    ("tests/test_make_split.py", "root-level test moved to tests/splitting/"),
    ("tests/test_sample_for_map.py", "root-level test moved to tests/sampling/"),
    ("tests/test_build_dataset.py", "root-level test moved to tests/dataset_build/"),
    ("tests/test_organize_dataset.py", "root-level test moved to tests/scripts/"),
    ("tests/test_upload_to_hf.py", "root-level test moved to tests/scripts/"),
    ("tests/test_extract.py", "root-level test moved to tests/stages/extract/"),
    ("tests/test_render.py", "root-level test moved to tests/readme/"),
    ("tests/test_pbf_meta.py", "root-level test moved to tests/metadata/"),
    ("tests/dataset_organize", "directory does not exist; tests live in tests/dataset_build/"),
    ("9 sub-folders", "stale test-folder count; current layout is 10 sub-folders"),
]


@pytest.mark.parametrize("path", PUBLIC_DOCS, ids=lambda p: p.relative_to(REPO_ROOT).as_posix())
def test_public_doc_exists(path: Path) -> None:
    """Each public doc must exist on disk."""
    assert path.is_file(), f"missing public doc: {path}"


@pytest.mark.parametrize("path", PUBLIC_DOCS, ids=lambda p: p.relative_to(REPO_ROOT).as_posix())
@pytest.mark.parametrize("needle,reason", FORBIDDEN, ids=lambda v: v[1] if isinstance(v, tuple) else v)
def test_public_docs_have_no_forbidden_patterns(
    path: Path, needle: str, reason: str,
) -> None:
    """Public docs must not contain forbidden stale references."""
    text = path.read_text()
    assert needle not in text, (
        f"{path.relative_to(REPO_ROOT)} contains forbidden pattern "
        f"{needle!r}: {reason}"
    )

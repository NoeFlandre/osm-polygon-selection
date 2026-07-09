"""HuggingFace dataset upload orchestration.

Pure functions and a small :class:`UploadConfig` dataclass for the
script-level runner. CLI: ``scripts/upload_to_hf.py`` is a thin
wrapper around :func:`osm_polygon_selection.hf_upload.runner.run`.

Submodules:

- :mod:`hf_upload.config`: defaults + dataclass.
- :mod:`hf_upload.token`: ``HF_TOKEN`` env lookup with fallback.
- :mod:`hf_upload.files`: file listing + relative path set.
- :mod:`hf_upload.cleanup`: stale-file deletion + dry-run planning.
- :mod:`hf_upload.runner`: orchestrator (token -> list -> delete -> upload).
"""

from osm_polygon_selection.hf_upload.config import (
    DEFAULT_REPO_ID,
    DEFAULT_ROOT,
    DEFAULT_IGNORE_PATTERNS,
    UploadConfig,
)
from osm_polygon_selection.hf_upload.runner import run

__all__ = [
    "DEFAULT_IGNORE_PATTERNS",
    "DEFAULT_REPO_ID",
    "DEFAULT_ROOT",
    "UploadConfig",
    "run",
]

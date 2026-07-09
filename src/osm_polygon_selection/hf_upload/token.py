"""HF token resolution.

Order of precedence:

1. ``HF_TOKEN`` environment variable (preferred for CI).
2. Cached token at ``~/.cache/huggingface/token``.

If neither is present, raise :class:`SystemExit` with a clear
message so the script prints the failure and exits non-zero.
"""

from __future__ import annotations

import os
from pathlib import Path


def get_token() -> str:
    """Return the HF token from env or cache, or raise SystemExit."""
    token = os.environ.get("HF_TOKEN")
    if token:
        return token
    cached = Path.home() / ".cache" / "huggingface" / "token"
    if cached.is_file():
        return cached.read_text().strip()
    raise SystemExit("no HF token found; set HF_TOKEN env var")


__all__ = ["get_token"]

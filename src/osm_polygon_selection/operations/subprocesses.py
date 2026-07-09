"""Subprocess helpers for stage 0/2/3 invocation.

Builds the ``uv run scripts/<stage>.py ...`` command lines used by
operator scripts. Does NOT actually invoke the subprocess; the
caller passes the result to :mod:`subprocess`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    pass


def build_stage0_command(
    pbf: Path,
    dst: Path,
    *,
    max_seconds: int | None = None,
) -> list[str]:
    """Build the ``stage0_extract`` CLI invocation."""
    cmd = ["uv", "run", "scripts/pipeline/stage0_extract.py", str(pbf), str(dst)]
    if max_seconds is not None:
        cmd += ["--max-seconds", str(max_seconds)]
    return cmd


def build_stage2_command(
    src: Path,
    whitelist: Path,
    out: Path,
) -> list[str]:
    """Build the ``stage2_filter`` CLI invocation."""
    return [
        "uv", "run", "scripts/pipeline/stage2_filter.py",
        str(src), str(whitelist), str(out),
    ]


def build_stage3_command(
    src: Path,
    shp: Path,
    out: Path,
) -> list[str]:
    """Build the ``stage3_classify`` CLI invocation."""
    return [
        "uv", "run", "scripts/pipeline/stage3_classify.py",
        str(src), str(shp), str(out),
    ]


def env_with_data_root(extra_env: dict[str, str] | None = None) -> dict[str, str]:
    """Return a copy of ``os.environ`` with the data-root env var set."""
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    return env


def run_with_env(
    cmd: Sequence[str],
    *,
    cwd: Path,
    env_extra: dict[str, str] | None = None,
    capture_output: bool = True,
    timeout: float | None = None,
) -> "subprocess.CompletedProcess[str]":
    """Run ``cmd`` in ``cwd`` with optional env additions.

    Returns the completed :class:`subprocess.CompletedProcess`.
    """
    import subprocess
    env = env_with_data_root(env_extra)
    return subprocess.run(
        list(cmd),
        cwd=str(cwd),
        env=env,
        capture_output=capture_output,
        text=True,
        timeout=timeout,
    )


def is_windows() -> bool:
    return sys.platform.startswith("win")


__all__ = [
    "build_stage0_command",
    "build_stage2_command",
    "build_stage3_command",
    "env_with_data_root",
    "is_windows",
    "run_with_env",
]

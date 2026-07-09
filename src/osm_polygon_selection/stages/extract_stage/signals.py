"""SIGALRM-based wall-clock timeout.

Used by the extract runner to enforce ``--max-seconds``. The
alarm raises :class:`WallClockTimeout` even when osmium is blocked
inside the FileProcessor (e.g. building the first-pass spatial
index for a giant multipolygon), which a pure deadline check in
the main loop cannot interrupt.
"""

from __future__ import annotations

import signal
from types import FrameType
from typing import Callable


class WallClockTimeout(Exception):
    """Raised by the SIGALRM handler when --max-seconds fires."""


def _alarm_handler(signum: int, frame: FrameType | None) -> None:
    raise WallClockTimeout()


def install(max_seconds: float) -> Callable[[], None]:
    """Install a SIGALRM handler that raises after ``max_seconds``.

    Returns a callable that restores the previous handler and
    cancels the alarm. Caller MUST call it in a ``finally``.
    """
    old_handler = signal.signal(signal.SIGALRM, _alarm_handler)
    signal.setitimer(signal.ITIMER_REAL, max_seconds)

    def _restore() -> None:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)

    return _restore


__all__ = ["WallClockTimeout", "install"]

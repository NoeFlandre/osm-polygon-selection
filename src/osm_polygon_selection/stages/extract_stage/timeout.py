"""SIGALRM-based per-polygon validation timeout.

Only works on the main thread. On a non-main thread the function
runs to completion with no enforcement (Python threads cannot
receive SIGALRM in a useful way).
"""

from __future__ import annotations

import signal
import threading
from typing import Callable, TypeVar

T = TypeVar("T")


class ValidationTimeout(Exception):
    """Raised when a per-polygon operation exceeds its time budget."""


def call_with_timeout(fn: Callable[[], T], timeout_s: float) -> T:
    """Run ``fn()`` with a SIGALRM-based timeout.

    Returns ``fn``'s return value, or raises :class:`ValidationTimeout`.
    On non-main threads the timeout is not enforced.
    """
    if threading.current_thread() is threading.main_thread():
        def _handler(signum, frame):
            raise ValidationTimeout()
        old_handler = signal.signal(signal.SIGALRM, _handler)
        signal.setitimer(signal.ITIMER_REAL, timeout_s)
        try:
            return fn()
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_handler)
    return fn()


__all__ = ["ValidationTimeout", "call_with_timeout"]

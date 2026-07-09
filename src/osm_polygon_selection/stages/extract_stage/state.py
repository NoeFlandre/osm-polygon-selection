"""Run-state dataclass for the extract stage.

Holds the counters + flags the runner threads through the osmium
loop. A simple namespace object; no I/O.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class RunState:
    """Counters + flags maintained across the osmium loop.

    Attributes:
        start_time: epoch seconds when the run started.
        last_progress: epoch seconds when progress was last written.
        last_progress_count: n_written + n_skipped at last progress write.
        deadline: epoch seconds at which --max-seconds fires; None = no cap.
        n_written: polygons written in THIS run.
        n_skipped: ids skipped via WAL.
        drops: per-reason drop tallies.
        hit_limit: --limit was reached.
        hit_time_limit: --max-seconds was reached.
    """

    start_time: float
    deadline: float | None
    last_progress: float = field(init=False)
    last_progress_count: int = field(init=False, default=0)
    n_written: int = field(init=False, default=0)
    n_skipped: int = field(init=False, default=0)
    drops: dict[str, int] = field(init=False, default_factory=dict)
    hit_limit: bool = field(init=False, default=False)
    hit_time_limit: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        self.last_progress = self.start_time


__all__ = ["RunState"]

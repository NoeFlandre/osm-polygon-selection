"""Write-ahead log (``.seen_ids``) for resumable extraction.

Every osm_id EVER considered (written OR dropped) goes into the
WAL. On resume, those ids are skipped entirely so we don't
re-evaluate the same OSM object twice. The buffer is flushed in
batches to avoid millions of disk syncs on a 32GB PBF.
"""

from __future__ import annotations

from pathlib import Path
from typing import IO

from osm_polygon_selection.stages.extract_stage.constants import WAL_BATCH


def load_seen_ids(wal_path: Path) -> set[int]:
    """Load all ids from the WAL. Skips corrupt lines silently."""
    seen: set[int] = set()
    if not wal_path.exists():
        return seen
    with wal_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                seen.add(int(line))
            except ValueError:
                continue
    return seen


class WALWriter:
    """Buffered writer for the seen-ids WAL.

    Flushes the buffered IDs every ``WAL_BATCH`` writes. Caller
    MUST call :meth:`flush` at end-of-iteration so any residual
    IDs hit disk.
    """

    def __init__(self, file_handle: IO[str]) -> None:
        self._file = file_handle
        self._buffer: list[str] = []

    def append(self, osm_id: int) -> None:
        self._buffer.append(f"{osm_id}\n")
        if len(self._buffer) >= WAL_BATCH:
            self.flush()

    def flush(self) -> None:
        if self._buffer:
            self._file.write("".join(self._buffer))
            self._file.flush()
            self._buffer.clear()


__all__ = ["WALWriter", "load_seen_ids"]

"""The osmium FileProcessor loop for stage 0.

Walks the PBF area-by-area, applies per-object filters (seen-set,
limit, deadline), and feeds each accepted object to the
``_record`` function via the parent ``stages.extract`` facade.
The loop is intentionally a thin helper so the runner stays
readable.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, cast

from osm_polygon_selection.stages import extract as _facade
from osm_polygon_selection.stages.extract_stage.progress import (
    rss_mb,
    write_progress_atomic,
)
from osm_polygon_selection.stages.extract_stage.state import RunState
from osm_polygon_selection.stages.extract_stage.wal import WALWriter


def _maybe_write_progress(
    state: RunState,
    progress_path: Path,
    pbf_size: int,
    force: bool = False,
) -> None:
    """Write .progress.json when warranted by time / count / force."""
    from osm_polygon_selection.stages.extract_stage.constants import (
        FIRST_PROGRESS_AFTER,
        PROGRESS_INTERVAL_S,
    )

    now = time.time()
    if (
        state.last_progress_count > 0
        and state.n_written + state.n_skipped - state.last_progress_count < 100_000
    ):
        return
    due_by_time = now - state.last_progress >= PROGRESS_INTERVAL_S
    due_by_count = (
        state.n_written > 0
        and state.n_written - state.last_progress_count >= FIRST_PROGRESS_AFTER
    )
    if not (force or due_by_time or due_by_count):
        return
    write_progress_atomic(
        progress_path,
        pbf_size=pbf_size,
        start_time=state.start_time,
        n_written=state.n_written,
        n_skipped=state.n_skipped,
        drops=state.drops,
    )
    elapsed = now - state.start_time
    rate = state.n_written / elapsed if elapsed > 0 else 0.0
    print(
        f"  progress: written={state.n_written:,} "
        f"skipped={state.n_skipped:,} "
        f"drops={sum(state.drops.values()):,} "
        f"elapsed={elapsed:.0f}s "
        f"rate={rate:.0f} pol/s "
        f"rss={rss_mb():.0f}MB",
        flush=True,
    )
    state.last_progress = now
    state.last_progress_count = state.n_written + state.n_skipped


def run_loop(
    pbf_path: Path,
    out_file,
    state: RunState,
    seen_ids: set[int],
    limit: int | None,
    progress_path: Path,
    pbf_size: int,
    wal: WALWriter,
) -> None:
    """Walk the PBF area-by-area, applying seen-set / limit / deadline filters."""
    for obj in _facade.osmium.FileProcessor(str(pbf_path)).with_areas():
        if state.deadline is not None and time.time() >= state.deadline:
            state.hit_time_limit = True
            return

        osm_id = obj.id
        if osm_id in seen_ids:
            state.n_skipped += 1
            continue

        if limit is not None and state.n_written >= limit:
            state.hit_limit = True
            return

        n = _facade._record(cast(Any, obj), out_file, state.drops)
        wal.append(osm_id)
        if n > 0:
            out_file.flush()
            state.n_written += 1
        seen_ids.add(osm_id)
        _maybe_write_progress(state, progress_path, pbf_size)


__all__ = ["run_loop"]

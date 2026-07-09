"""Final-progress + run-log + summary-log writing for stage 0.

The runner calls these after the main loop exits (limit / time /
clean completion / SIGALRM).
"""

from __future__ import annotations

import time
from pathlib import Path

from osm_polygon_selection.stages.extract_stage.progress import rss_mb
from osm_polygon_selection.stages.extract_stage.run_log import (
    build_run_log_payload,
    write_run_log,
)
from osm_polygon_selection.stages.extract_stage.state import RunState


def log_run_summary(
    state: RunState,
    *,
    max_seconds: float | None,
    limit: int | None,
    total_seen: int,
) -> None:
    """Emit the human-readable summary line at the end of a run."""
    elapsed = time.time() - state.start_time
    if state.hit_time_limit:
        print(
            f"wall-clock limit ({max_seconds:.0f}s) reached: "
            f"written={state.n_written:,} in {elapsed:.0f}s. "
            f"Re-run (no --max-seconds, or higher) to resume. "
            f"Already-seen ids ({state.n_skipped:,}) will be skipped via WAL.",
            flush=True,
        )
    elif state.hit_limit:
        print(
            f"limit reached: written={state.n_written:,} of limit={limit:,} "
            f"in {elapsed:.0f}s. Run again (no --limit, or higher) to resume.",
            flush=True,
        )
    else:
        print(
            f"done: written={state.n_written:,} skipped={state.n_skipped:,} "
            f"in {elapsed:.0f}s",
            flush=True,
        )
    print(f"  drops: {state.drops}", flush=True)
    print(f"  total osm ids seen: {total_seen:,}", flush=True)
    print(f"  final rss={rss_mb():.0f}MB", flush=True)


def write_final_artifacts(
    state: RunState,
    *,
    pbf_path: Path,
    pbf_size: int,
    out_path: Path,
    wal_path: Path,
    progress_path: Path,
    log_path: Path,
    limit: int | None,
    total_seen: int,
) -> None:
    """Write the run log (.run.json) from the final RunState."""
    write_run_log(
        log_path,
        build_run_log_payload(
            pbf_path=pbf_path,
            pbf_size=pbf_size,
            out_path=out_path,
            wal_path=wal_path,
            progress_path=progress_path,
            log_path=log_path,
            start_time=state.start_time,
            limit=limit,
            limit_reached=state.hit_limit,
            drops=state.drops,
            n_written=state.n_written,
            n_skipped=state.n_skipped,
            total_seen=total_seen,
        ),
    )
    print(f"wrote run log to {log_path}", flush=True)


__all__ = ["log_run_summary", "write_final_artifacts"]

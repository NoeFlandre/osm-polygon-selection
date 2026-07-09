"""Stage 0 (extract) public orchestration.

Thin coordinator that wires together:
  - state (RunState)
  - signals (SIGALRM wall-clock cap)
  - loop (osmium FileProcessor walker)
  - finalization (run log + summary print)

Reads ``osmium`` and ``_record`` through the parent ``stages.extract``
facade so tests can monkeypatch the facade's symbols
(e.g. ``osm_polygon_selection.stages.extract.osmium.FileProcessor``)
without losing their effect on this module.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

from osm_polygon_selection.stages.extract_stage.constants import (
    LOG_SUFFIX,
    PROGRESS_SUFFIX,
    WAL_SUFFIX,
)
from osm_polygon_selection.stages.extract_stage.finalization import (
    log_run_summary,
    write_final_artifacts,
)
from osm_polygon_selection.stages.extract_stage.loop import run_loop
from osm_polygon_selection.stages.extract_stage.progress import rss_mb
from osm_polygon_selection.stages.extract_stage.signals import (
    WallClockTimeout,
    install as install_alarm,
)
from osm_polygon_selection.stages.extract_stage.state import RunState
from osm_polygon_selection.stages.extract_stage.wal import (
    WALWriter,
    load_seen_ids,
)


def _log(msg: str) -> None:
    """Log to stderr with timestamp."""
    ts = datetime.now(tz=timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def extract(
    pbf_path: Path,
    out_path: Path,
    *,
    limit: int | None = None,
    max_seconds: float | None = None,
) -> int:
    """Stream a PBF, write each polygon to JSONL. Resumable + stoppable."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wal_path = out_path.with_suffix(out_path.suffix + WAL_SUFFIX)
    progress_path = out_path.with_suffix(out_path.suffix + PROGRESS_SUFFIX)
    log_path = out_path.with_suffix(out_path.suffix + LOG_SUFFIX)

    seen_ids = load_seen_ids(wal_path)
    if seen_ids:
        _log(f"resuming: {len(seen_ids):,} OSM objects already seen (skipped)")

    pbf_size = pbf_path.stat().st_size if pbf_path.exists() else 0
    start_time = time.time()
    _log(f"start extract pbf={pbf_path} size={pbf_size / 1e9:.2f}GB")
    _log(f"  output={out_path}")
    _log(f"  wal={wal_path}")
    _log(f"  progress={progress_path}")
    _log(f"  log={log_path}")
    _log(f"  limit={limit if limit else 'none'}")
    _log(f"  rss={rss_mb():.0f}MB")

    deadline = (start_time + max_seconds) if max_seconds is not None else None
    state = RunState(start_time=start_time, deadline=deadline)

    restore_alarm = None
    if deadline is not None:
        assert max_seconds is not None
        restore_alarm = install_alarm(max_seconds)

    try:
        with out_path.open("a") as fout, wal_path.open("a") as fwal:
            wal = WALWriter(fwal)
            try:
                run_loop(
                    pbf_path=pbf_path,
                    out_file=fout,
                    state=state,
                    seen_ids=seen_ids,
                    limit=limit,
                    progress_path=progress_path,
                    pbf_size=pbf_size,
                    wal=wal,
                )
            except WallClockTimeout:
                state.hit_time_limit = True
                _log("wall-clock timeout received inside main loop; exiting cleanly")

            try:
                wal.flush()
            except WallClockTimeout:
                state.hit_time_limit = True
    finally:
        if restore_alarm is not None:
            restore_alarm()

    log_run_summary(state, max_seconds=max_seconds, limit=limit, total_seen=len(seen_ids))
    write_final_artifacts(
        state,
        pbf_path=pbf_path,
        pbf_size=pbf_size,
        out_path=out_path,
        wal_path=wal_path,
        progress_path=progress_path,
        log_path=log_path,
        limit=limit,
        total_seen=len(seen_ids),
    )
    return state.n_written


__all__ = ["extract"]

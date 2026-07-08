"""Stage 0 (extract) orchestration.

The streaming PBF -> JSONL pipeline. Resumable via WAL,
observable via .progress.json, stoppable via --limit and
--max-seconds.

The runner reads ``osmium`` and ``record`` through the parent
``stages.extract`` facade so tests can monkeypatch the facade's
symbols (e.g. ``osm_polygon_selection.stages.extract.osmium.FileProcessor``)
without losing their effect on this module.
"""

from __future__ import annotations

import signal
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from osm_polygon_selection.stages import extract as _facade
from osm_polygon_selection.stages.extract_stage.constants import (
    FIRST_PROGRESS_AFTER,
    LOG_SUFFIX,
    PROGRESS_INTERVAL_S,
    PROGRESS_SUFFIX,
    WAL_SUFFIX,
)
from osm_polygon_selection.stages.extract_stage.progress import (
    rss_mb,
    write_progress_atomic,
)
from osm_polygon_selection.stages.extract_stage.run_log import (
    build_run_log_payload,
    write_run_log,
)
from osm_polygon_selection.stages.extract_stage.wal import (
    WALWriter,
    load_seen_ids,
)


def _log(msg: str) -> None:
    """Log to stderr with timestamp."""
    ts = datetime.now(tz=timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


class _WallClockTimeout(Exception):
    """Raised by SIGALRM handler when --max-seconds expires."""


def extract(
    pbf_path: Path,
    out_path: Path,
    *,
    limit: int | None = None,
    max_seconds: float | None = None,
) -> int:
    """Stream a PBF, write each polygon to JSONL. Resumable + stoppable.

    Args:
        pbf_path: input .osm.pbf file.
        out_path: output .jsonl file (created or appended to).
        limit: stop after this many NEW polygons in this run.
        max_seconds: stop after this many seconds of wall-clock time.

    Returns:
        Number of polygons written in THIS run (excludes already-WAL'd
        ones from prior runs).
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wal_path = out_path.with_suffix(out_path.suffix + WAL_SUFFIX)
    progress_path = out_path.with_suffix(out_path.suffix + PROGRESS_SUFFIX)
    log_path = out_path.with_suffix(out_path.suffix + LOG_SUFFIX)

    seen_ids = load_seen_ids(wal_path)
    if seen_ids:
        _log(f"resuming: {len(seen_ids):,} OSM objects already seen (skipped)")

    drops: dict[str, int] = {}

    pbf_size = pbf_path.stat().st_size if pbf_path.exists() else 0
    start_time = time.time()
    _log(f"start extract pbf={pbf_path} size={pbf_size / 1e9:.2f}GB")
    _log(f"  output={out_path}")
    _log(f"  wal={wal_path}")
    _log(f"  progress={progress_path}")
    _log(f"  log={log_path}")
    _log(f"  limit={limit if limit else 'none'}")
    _log(f"  rss={rss_mb():.0f}MB")

    n_written = 0
    n_skipped = 0
    last_progress = start_time
    last_progress_count = 0
    hit_limit = False
    hit_time_limit = False
    deadline = (start_time + max_seconds) if max_seconds is not None else None

    def _alarm_handler(signum, frame):
        raise _WallClockTimeout()

    old_handler = None
    if deadline is not None:
        old_handler = signal.signal(signal.SIGALRM, _alarm_handler)
        assert max_seconds is not None
        signal.setitimer(signal.ITIMER_REAL, max_seconds)

    def maybe_write_progress(force: bool = False) -> None:
        nonlocal last_progress, last_progress_count
        now = time.time()
        if (
            last_progress_count > 0
            and n_written + n_skipped - last_progress_count < 100_000
        ):
            return
        due_by_time = now - last_progress >= PROGRESS_INTERVAL_S
        due_by_count = (
            n_written > 0
            and n_written - last_progress_count >= FIRST_PROGRESS_AFTER
        )
        if not (force or due_by_time or due_by_count):
            return
        write_progress_atomic(
            progress_path,
            pbf_size=pbf_size,
            start_time=start_time,
            n_written=n_written,
            n_skipped=n_skipped,
            drops=drops,
        )
        elapsed = now - start_time
        rate = n_written / elapsed if elapsed > 0 else 0.0
        _log(
            f"  progress: written={n_written:,} "
            f"skipped={n_skipped:,} "
            f"drops={sum(drops.values()):,} "
            f"elapsed={elapsed:.0f}s "
            f"rate={rate:.0f} pol/s "
            f"rss={rss_mb():.0f}MB"
        )
        last_progress = now
        last_progress_count = n_written + n_skipped

    try:
        with out_path.open("a") as fout, wal_path.open("a") as fwal:
            wal = WALWriter(fwal)
            try:
                for obj in _facade.osmium.FileProcessor(str(pbf_path)).with_areas():
                    if deadline is not None and time.time() >= deadline:
                        hit_time_limit = True
                        break

                    osm_id = obj.id
                    if osm_id in seen_ids:
                        n_skipped += 1
                        continue

                    if limit is not None and n_written >= limit:
                        hit_limit = True
                        break

                    n = _facade._record(cast(Any, obj), fout, drops)
                    wal.append(osm_id)
                    if n > 0:
                        fout.flush()
                        n_written += 1
                    seen_ids.add(osm_id)
                    maybe_write_progress()
            except _WallClockTimeout:
                hit_time_limit = True
                _log("wall-clock timeout received inside main loop; exiting cleanly")

            try:
                wal.flush()
            except _WallClockTimeout:
                hit_time_limit = True
    finally:
        if old_handler is not None:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_handler)

    maybe_write_progress(force=True)

    elapsed = time.time() - start_time
    if hit_time_limit:
        _log(
            f"wall-clock limit ({max_seconds:.0f}s) reached: "
            f"written={n_written:,} in {elapsed:.0f}s. "
            f"Re-run (no --max-seconds, or higher) to resume. "
            f"Already-seen ids ({n_skipped:,}) will be skipped via WAL."
        )
    elif hit_limit:
        _log(
            f"limit reached: written={n_written:,} of limit={limit:,} "
            f"in {elapsed:.0f}s. Run again (no --limit, or higher) to resume."
        )
    else:
        _log(
            f"done: written={n_written:,} skipped={n_skipped:,} "
            f"in {elapsed:.0f}s"
        )
    _log(f"  drops: {drops}")
    _log(f"  total osm ids seen: {len(seen_ids):,}")
    _log(f"  final rss={rss_mb():.0f}MB")

    write_run_log(
        log_path,
        build_run_log_payload(
            pbf_path=pbf_path,
            pbf_size=pbf_size,
            out_path=out_path,
            wal_path=wal_path,
            progress_path=progress_path,
            log_path=log_path,
            start_time=start_time,
            limit=limit,
            limit_reached=hit_limit,
            drops=drops,
            n_written=n_written,
            n_skipped=n_skipped,
            total_seen=len(seen_ids),
        ),
    )
    _log(f"wrote run log to {log_path}")
    return n_written


__all__ = ["extract"]

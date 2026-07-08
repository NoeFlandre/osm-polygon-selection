"""Final run log (.run.json) writer.

The run log is the immutable record of one extract run. It
captures inputs, outputs, counts, drops, and timing.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from osm_polygon_selection.stages.extract_stage.progress import rss_mb


def build_run_log_payload(
    *,
    pbf_path: Path,
    pbf_size: int,
    out_path: Path,
    wal_path: Path,
    progress_path: Path,
    log_path: Path,
    start_time: float,
    limit: int | None,
    limit_reached: bool,
    drops: dict[str, int],
    n_written: int,
    n_skipped: int,
    total_seen: int,
) -> dict:
    """Build the .run.json payload. Pure (no IO)."""
    elapsed = time.time() - start_time
    return {
        "pbf_path": str(pbf_path),
        "pbf_size_bytes": pbf_size,
        "output_path": str(out_path),
        "wal_path": str(wal_path),
        "progress_path": str(progress_path),
        "start_time_utc": datetime.fromtimestamp(
            start_time, tz=timezone.utc,
        ).isoformat(),
        "end_time_utc": datetime.now(tz=timezone.utc).isoformat(),
        "elapsed_seconds": elapsed,
        "polygons_written": n_written,
        "polygons_skipped_resume": n_skipped,
        "limit": limit,
        "limit_reached": limit_reached,
        "drops": dict(drops),
        "total_osm_ids_seen": total_seen,
        "peak_rss_mb": round(rss_mb(), 1),
    }


def write_run_log(log_path: Path, payload: dict) -> None:
    """Write the run log to ``log_path``. Non-atomic; this is end-of-run."""
    log_path.write_text(json.dumps(payload, indent=2))


__all__ = ["build_run_log_payload", "write_run_log"]

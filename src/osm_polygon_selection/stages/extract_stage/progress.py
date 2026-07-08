"""Live .progress.json writer + helper telemetry.

The progress payload is the contract with operators: they can
``cat .progress.json`` at any time to see where the run is. All
keys are stable.
"""

from __future__ import annotations

import json
import resource
import time
from datetime import datetime, timezone
from pathlib import Path


def rss_mb() -> float:
    """Current process peak RSS in MB (macOS reports bytes, Linux KB)."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1_000_000.0


def build_progress_payload(
    *,
    pbf_size: int,
    start_time: float,
    n_written: int,
    n_skipped: int,
    drops: dict[str, int],
) -> dict:
    """Return the .progress.json payload. Pure (no IO)."""
    elapsed = time.time() - start_time
    rate = n_written / elapsed if elapsed > 0 else 0.0
    return {
        "pbf_size_bytes": pbf_size,
        "elapsed_seconds": round(elapsed, 1),
        "polygons_written": n_written,
        "polygons_skipped_resume": n_skipped,
        "drops": dict(drops),
        "drop_total": sum(drops.values()),
        "throughput_pol_per_sec": round(rate, 1),
        "rss_mb": round(rss_mb(), 1),
        "last_update_utc": datetime.now(tz=timezone.utc).isoformat(),
    }


def write_progress(progress_path: Path, payload: dict) -> None:
    """Atomically rewrite the progress file with the given payload."""
    tmp = progress_path.with_suffix(progress_path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(progress_path)


def write_progress_atomic(
    progress_path: Path,
    *,
    pbf_size: int,
    start_time: float,
    n_written: int,
    n_skipped: int,
    drops: dict[str, int],
) -> None:
    """Convenience: build + write the payload in one call."""
    write_progress(
        progress_path,
        build_progress_payload(
            pbf_size=pbf_size,
            start_time=start_time,
            n_written=n_written,
            n_skipped=n_skipped,
            drops=drops,
        ),
    )


__all__ = [
    "build_progress_payload",
    "rss_mb",
    "write_progress",
    "write_progress_atomic",
]

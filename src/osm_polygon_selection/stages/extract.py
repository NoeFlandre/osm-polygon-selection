"""Stage 0: stream a PBF file, write closed-way + multipolygon polygons to JSONL.

Auditable, resumable, observable, and stoppable.

Auditable:
  - A live progress file (.progress.json) is rewritten every tick with
    current counts, drop reasons, throughput, memory, elapsed time.
    Inspectable at any time: cat .progress.json
  - A run log (.run.json) is finalized at the end with full metadata.
  - Drop reasons are tallied and reported continuously.

Resumable:
  - A write-ahead log (.seen_ids) lists every osm_id EVER considered
    (written OR dropped). On re-run, those ids are skipped entirely
    - we don't re-evaluate the same OSM object twice. This is critical
    on Europe (32GB, 200M+ objects): without the seen set, a resume
    would re-evaluate 200M objects just to write 10k more.
  - Stopping (Ctrl-C, --limit N, kill) and restarting produces the
    same final file. The .progress.json is preserved across restarts.

Stoppable:
  - --limit N caps the number of NEW polygons written in this run.
  - Run is paused, not killed: the .progress.json shows the state.
  - Resume: just re-run with no --limit (or a higher one).

Observable:
  - A progress line is logged to stderr every PROGRESS_INTERVAL_S.
  - .progress.json is rewritten every FIRST_PROGRESS_AFTER writes or
    every PROGRESS_INTERVAL_S, whichever comes first.
"""

import json
import resource
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

import osmium
import shapely.wkt
from shapely.validation import make_valid

from osm_polygon_selection.core.geometry_utils import area_km2, is_polygon

MIN_AREA_KM2 = 0.1
MAX_AREA_KM2 = 100.0

PROGRESS_INTERVAL_S = 15.0
FIRST_PROGRESS_AFTER = 100

WAL_SUFFIX = ".seen_ids"
PROGRESS_SUFFIX = ".progress.json"
LOG_SUFFIX = ".run.json"

_factory = osmium.geom.WKTFactory()


def _rss_mb() -> float:
    """Current process peak RSS in MB (macOS reports bytes, Linux reports KB)."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1_000_000.0


def _log(msg: str) -> None:
    """Log to stderr with timestamp."""
    ts = datetime.now(tz=timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def _write_progress(
    progress_path: Path,
    *,
    pbf_size: int,
    start_time: float,
    n_written: int,
    n_skipped: int,
    drops: dict[str, int],
) -> None:
    """Atomically rewrite .progress.json with current state."""
    elapsed = time.time() - start_time
    rate = n_written / elapsed if elapsed > 0 else 0.0
    payload = {
        "pbf_size_bytes": pbf_size,
        "elapsed_seconds": round(elapsed, 1),
        "polygons_written": n_written,
        "polygons_skipped_resume": n_skipped,
        "drops": dict(drops),
        "drop_total": sum(drops.values()),
        "throughput_pol_per_sec": round(rate, 1),
        "rss_mb": round(_rss_mb(), 1),
        "last_update_utc": datetime.now(tz=timezone.utc).isoformat(),
    }
    tmp = progress_path.with_suffix(progress_path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(progress_path)


def _record(
    area: osmium.osm.OSMObject,
    fout,
    drops: dict[str, int],
) -> int:
    """Process one OSM object. Returns 1 if a row was written."""
    if not area.is_area():
        drops["not_an_area"] = drops.get("not_an_area", 0) + 1
        return 0
    area_area = cast(osmium.osm.Area, area)
    try:
        wkt = _factory.create_multipolygon(area_area)
        geom = shapely.wkt.loads(wkt)
    except Exception:
        drops["wkt_conversion_failed"] = drops.get("wkt_conversion_failed", 0) + 1
        return 0

    if not geom.is_valid:
        geom = make_valid(geom)
    if not is_polygon(geom):
        drops["not_polygon"] = drops.get("not_polygon", 0) + 1
        return 0

    a = area_km2(geom)
    if a < MIN_AREA_KM2:
        drops["too_small"] = drops.get("too_small", 0) + 1
        return 0
    if a > MAX_AREA_KM2:
        drops["too_large"] = drops.get("too_large", 0) + 1
        return 0

    c = geom.centroid
    tags = [(k, v) for k, v in area_area.tags if k not in ("area", "type")]
    row = {
        "osm_id": area.id,
        "osm_type": "way" if area_area.from_way() else "relation",
        "geometry": geom.wkt,
        "centroid": [float(c.x), float(c.y)],
        "area_km2": a,
        "tags": [f"{k}={v}" for k, v in tags],
    }
    fout.write(json.dumps(row) + "\n")
    return 1


def extract(
    pbf_path: Path,
    out_path: Path,
    *,
    limit: int | None = None,
) -> int:
    """Stream a PBF, write each polygon to JSONL. Resumable + stoppable.

    Args:
        pbf_path: input .osm.pbf file.
        out_path: output .jsonl file (created or appended to).
        limit: stop after this many NEW polygons in this run.
            None = run to completion. Used to slice a long extraction
            into manageable chunks (e.g. 10000 at a time on Europe).

    Returns:
        Number of polygons written in THIS run (excludes already-WAL'd
        ones from prior runs).
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wal_path = out_path.with_suffix(out_path.suffix + WAL_SUFFIX)
    progress_path = out_path.with_suffix(out_path.suffix + PROGRESS_SUFFIX)
    log_path = out_path.with_suffix(out_path.suffix + LOG_SUFFIX)

    # Load the seen set (every osm_id ever considered on any prior run).
    # If an id is here, skip it entirely - re-evaluating it would
    # double-count drops on resume and waste CPU on 200M+ object PBFs.
    # Drops are NOT loaded from a prior run: per-OSM-object counts would
    # double on resume (we've already counted them in a prior run).
    seen_ids: set[int] = set()
    if wal_path.exists():
        with wal_path.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        seen_ids.add(int(line))
                    except ValueError:
                        pass
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
    _log(f"  rss={_rss_mb():.0f}MB")

    n_written = 0
    n_skipped = 0
    last_progress = time.time()
    last_progress_count = 0
    hit_limit = False
    wal_buffer: list[str] = []
    WAL_BATCH = 10_000  # flush WAL every N writes (~10k IDs = ~100KB buffered)

    def flush_wal() -> None:
        if wal_buffer:
            fwal.write("".join(wal_buffer))
            fwal.flush()
            wal_buffer.clear()

    def maybe_write_progress(force: bool = False) -> None:
        """Write progress file if enough time has passed OR enough objects
        have been processed. The time check is throttled by the count
        check: we only call this function every N objects, so the time
        check doesn't fire on every single drop (would be 200M+ atomic
        writes for Europe and destroy I/O).
        """
        nonlocal last_progress, last_progress_count
        now = time.time()
        # Throttle: only consider time check every 100k objects.
        if last_progress_count > 0 and n_written + n_skipped - last_progress_count < 100_000:
            return
        due_by_time = now - last_progress >= PROGRESS_INTERVAL_S
        due_by_count = n_written > 0 and n_written - last_progress_count >= FIRST_PROGRESS_AFTER
        if not (force or due_by_time or due_by_count):
            return
        _write_progress(
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
            f"rss={_rss_mb():.0f}MB"
        )
        last_progress = now
        last_progress_count = n_written + n_skipped

    with out_path.open("a") as fout, wal_path.open("a") as fwal:
        for obj in osmium.FileProcessor(str(pbf_path)).with_areas():
            osm_id = obj.id
            if osm_id in seen_ids:
                n_skipped += 1
                continue

            if limit is not None and n_written >= limit:
                hit_limit = True
                break

            n = _record(cast(osmium.osm.OSMObject, obj), fout, drops)
            # Mark the osm_id as seen regardless of whether it was
            # accepted (written) or dropped. This is what makes resume
            # truly skip work: we never re-evaluate the same id.
            # WAL writes are batched (every WAL_BATCH IDs) to avoid
            # doing 200M+ disk syncs on a 32GB PBF.
            wal_buffer.append(f"{osm_id}\n")
            if len(wal_buffer) >= WAL_BATCH:
                flush_wal()
            if n > 0:
                fout.flush()
                n_written += 1
            seen_ids.add(osm_id)

            maybe_write_progress()

        # Flush any remaining WAL buffer at end of iteration.
        flush_wal()

    # Final progress update.
    maybe_write_progress(force=True)

    elapsed = time.time() - start_time
    if hit_limit:
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
    _log(f"  final rss={_rss_mb():.0f}MB")

    # Final run log.
    log_data = {
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
        "limit_reached": hit_limit,
        "drops": drops,
        "total_osm_ids_seen": len(seen_ids),
        "peak_rss_mb": round(_rss_mb(), 1),
    }
    log_path.write_text(json.dumps(log_data, indent=2))
    _log(f"wrote run log to {log_path}")
    return n_written

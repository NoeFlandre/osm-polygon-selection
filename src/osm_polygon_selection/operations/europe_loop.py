"""Per-country Europe pipeline orchestration.

Implements the multi-country loop: for each country in the
EU + Europe list, check if its 03_classified.jsonl exists, and
if not download + extract (with a wall-clock cap) + filter +
classify. The per-country functions return a status string so
the caller can decide whether to skip / retry / give up.
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from subprocess import Popen

from osm_polygon_selection.operations.downloads import (
    build_curl_command,
    geofabrik_country_url,
    pbf_is_present,
)
from osm_polygon_selection.operations.subprocesses import (
    build_stage0_command,
    build_stage2_command,
    build_stage3_command,
    env_with_data_root,
    run_with_env,
)


# All European countries, smallest first.
EUROPEAN_COUNTRIES: list[str] = [
    "monaco", "andorra", "liechtenstein", "guernsey-jersey", "isle-of-man",
    "faroe-islands", "malta", "azores", "kosovo", "montenegro", "cyprus",
    "luxembourg", "albania", "iceland", "moldova", "estonia", "latvia",
    "bosnia-herzegovina", "bulgaria", "croatia", "lithuania", "serbia",
    "slovenia", "hungary", "romania", "greece", "slovakia", "belarus",
    "portugal", "denmark", "switzerland", "turkey", "belgium", "finland",
    "austria", "sweden", "ukraine", "czech-republic", "norway",
    "netherlands", "spain", "poland", "italy", "united-kingdom",
    "germany", "france",
]

# Per-iteration extract timeout. After this we stop waiting; the
# background stage-0 process continues running on the operator
# machine and the next operator session can pick it up via the WAL.
DEFAULT_EXTRACT_WAIT_S = 120

# Geofabrik admin-0 shapefile for stage 3 classification.
NATURAL_EARTH_SHP = "data/reference/natural_earth/ne_110m_admin_0_countries.shp"


def is_classified(country_dir: Path) -> bool:
    """True if 03_classified.jsonl exists and is non-empty."""
    p = country_dir / "03_classified.jsonl"
    return p.exists() and p.stat().st_size > 0


def has_extracted(country_dir: Path) -> bool:
    """True if 01_extracted.jsonl exists and has content."""
    p = country_dir / "01_extracted.jsonl"
    return p.exists() and p.stat().st_size > 100


def read_progress(country_dir: Path) -> dict:
    """Read 01_extracted.jsonl.progress.json if it exists."""
    p = country_dir / "01_extracted.jsonl.progress.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open() as f:
        return sum(1 for _ in f)


def download_country_pbf(raw_dir: Path, country: str) -> bool:
    """Download the country PBF via curl. Returns True if usable."""
    target = raw_dir / f"{country}-latest.osm.pbf"
    if pbf_is_present(target):
        return True
    raw_dir.mkdir(parents=True, exist_ok=True)
    cmd = build_curl_command(geofabrik_country_url(country), target)
    run_with_env(cmd, cwd=Path.cwd(), capture_output=True, timeout=600)
    return pbf_is_present(target)


def start_extract(
    *,
    pbf: Path,
    dst: Path,
    hdd_root: Path,
    proj: Path,
) -> "Popen[bytes]":
    """Start a stage-0 extract subprocess; returns the Popen handle."""
    cmd = build_stage0_command(pbf, dst)
    return subprocess.Popen(
        cmd,
        env=env_with_data_root({"OSM_DATA_ROOT": str(hdd_root)}),
        cwd=str(proj),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wait_for_extract(
    proc: "Popen[bytes]",
    *,
    poll_fn: Callable[[], float] = time.time,
    sleep_fn: Callable[[float], None] = time.sleep,
    max_s: int = DEFAULT_EXTRACT_WAIT_S,
) -> str:
    """Wait up to ``max_s`` for the extract to finish.

    Returns ``"done"``, ``"failed"``, or ``"timeout"``.
    """
    start = poll_fn()
    while poll_fn() - start < max_s:
        if proc.poll() is not None:
            return "done" if proc.returncode == 0 else "failed"
        sleep_fn(2)
    return "timeout"


def complete_stages(
    *,
    country: str,
    proc_dir: Path,
    hdd_root: Path,
    proj: Path,
    shp: Path,
) -> int:
    """Run stages 2 + 3 for ``country``. Returns polygon count or 0."""
    src = proc_dir / country / "01_extracted.jsonl"
    filt = proc_dir / country / "02_filtered.jsonl"
    cls = proc_dir / country / "03_classified.jsonl"
    env = env_with_data_root({"OSM_DATA_ROOT": str(hdd_root)})

    r1 = run_with_env(
        build_stage2_command(src, hdd_root / "whitelist.json", filt),
        cwd=proj, env_extra=env, timeout=60,
    )
    if r1.returncode != 0:
        return 0

    r2 = run_with_env(
        build_stage3_command(filt, shp, cls),
        cwd=proj, env_extra=env, timeout=60,
    )
    if r2.returncode != 0:
        return 0

    return count_lines(cls)


__all__ = [
    "DEFAULT_EXTRACT_WAIT_S",
    "EUROPEAN_COUNTRIES",
    "NATURAL_EARTH_SHP",
    "complete_stages",
    "count_lines",
    "download_country_pbf",
    "has_extracted",
    "is_classified",
    "read_progress",
    "start_extract",
    "wait_for_extract",
]

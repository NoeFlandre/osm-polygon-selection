#!/usr/bin/env python3
"""Process all European countries end-to-end, with proper backgrounding.

For each country:
1. If 03_classified.jsonl exists, skip (done).
2. Otherwise, launch stage 0 in background. Poll progress.json.
3. If extract takes too long for a single agent call, save state
   and continue (the WAL is preserved across agent calls).
4. Once extract is done, run filter + classify (fast).
"""

import json
import os
import subprocess
import time
from pathlib import Path

HDD = Path("/Volumes/Seagate M3/osm-polygon-selection")
PROC = HDD / "processed"
RAW = HDD / "raw"
PROJ = Path("/Users/noeflandre/osm-polygon-selection")

# All European countries, smallest first.
COUNTRIES = [
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

# Per-call extract timeout. After this we stop waiting; the background
# process continues running on the user's machine.
EXTRACT_WAIT_S = 120


def download(country: str) -> bool:
    """Download the PBF if not already on disk."""
    target = RAW / f"{country}-latest.osm.pbf"
    if target.exists() and target.stat().st_size > 1000:
        return True
    RAW.mkdir(parents=True, exist_ok=True)
    url = f"https://download.geofabrik.de/europe/{country}-latest.osm.pbf"
    print(f"  downloading {country} from {url}...")
    try:
        r = subprocess.run(
            ["curl", "-L", "-s", "-o", str(target), url],
            timeout=600,
        )
        return target.exists() and target.stat().st_size > 1000
    except subprocess.TimeoutExpired:
        print(f"  download timeout for {country}")
        return False


def is_done(country: str) -> bool:
    p = PROC / country / "03_classified.jsonl"
    return p.exists() and p.stat().st_size > 0


def has_polygons(country: str) -> bool:
    """True if 01_extracted.jsonl has at least some polygons."""
    p = PROC / country / "01_extracted.jsonl"
    return p.exists() and p.stat().st_size > 100


def get_status(country: str) -> dict:
    """Read .progress.json if it exists."""
    p = PROC / country / "01_extracted.jsonl.progress.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def run_extract_bg(country: str) -> subprocess.Popen:
    """Start stage 0 in background, return Popen handle."""
    src = RAW / f"{country}-latest.osm.pbf"
    dst = PROC / country / "01_extracted.jsonl"
    env = os.environ.copy()
    env["OSM_DATA_ROOT"] = str(HDD)
    return subprocess.Popen(
        ["uv", "run", "scripts/stage0_extract.py", str(src), str(dst)],
        env=env, cwd=str(PROJ),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def wait_extract(country: str, proc: subprocess.Popen, max_s: int) -> str:
    """Wait up to max_s for extract to finish. Returns 'done' | 'timeout' | 'failed'."""
    start = time.time()
    while time.time() - start < max_s:
        if proc.poll() is not None:
            return "done" if proc.returncode == 0 else "failed"
        time.sleep(2)
    return "timeout"


def complete_stages(country: str) -> int:
    """Run stages 2 and 3. Returns count of classified polygons, or 0 on failure."""
    src = PROC / country / "01_extracted.jsonl"
    filt = PROC / country / "02_filtered.jsonl"
    cls = PROC / country / "03_classified.jsonl"
    env = os.environ.copy()
    env["OSM_DATA_ROOT"] = str(HDD)
    try:
        r1 = subprocess.run(
            ["uv", "run", "scripts/stage2_filter.py", str(src),
             str(HDD / "whitelist.json"), str(filt)],
            env=env, cwd=str(PROJ), capture_output=True, text=True, timeout=60,
        )
        if r1.returncode != 0:
            print(f"  stage2 FAILED: {r1.stderr[-200:]}")
            return 0
        r2 = subprocess.run(
            ["uv", "run", "scripts/stage3_classify.py", str(filt),
             "data/reference/natural_earth/ne_110m_admin_0_countries.shp",
             str(cls)],
            env=env, cwd=str(PROJ), capture_output=True, text=True, timeout=60,
        )
        if r2.returncode != 0:
            print(f"  stage3 FAILED: {r2.stderr[-200:]}")
            return 0
        if cls.exists():
            with cls.open() as f:
                return sum(1 for _ in f)
    except subprocess.TimeoutExpired:
        print(f"  stages timeout for {country}")
    return 0


def main() -> int:
    pending = [c for c in COUNTRIES if not is_done(c)]
    done = [c for c in COUNTRIES if is_done(c)]
    print(f"=== Status: {len(done)} done, {len(pending)} pending ===")
    for c in done:
        cls = PROC / c / "03_classified.jsonl"
        n = sum(1 for _ in cls.open()) if cls.exists() else 0
        print(f"  DONE  {c}: {n}")
    print(f"=== Processing {len(pending)} pending ===")

    for i, country in enumerate(pending, 1):
        print(f"\n[{i}/{len(pending)}] {country}")

        # Skip if extract already done from a prior run.
        if not has_polygons(country):
            if not download(country):
                print(f"  download failed, skipping")
                continue
            print(f"  starting extract (will wait up to {EXTRACT_WAIT_S}s)...")
            (PROC / country).mkdir(parents=True, exist_ok=True)
            proc = run_extract_bg(country)
            status = wait_extract(country, proc, EXTRACT_WAIT_S)
            if status == "timeout":
                print(f"  extract still running, leaving in background")
                continue
            elif status == "failed":
                print(f"  extract failed, skipping")
                continue
            else:
                print(f"  extract done")

        if has_polygons(country):
            n = complete_stages(country)
            print(f"  -> {n} classified")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""CLI builders for operator scripts.

Each function returns an :class:`argparse.ArgumentParser` for a
specific operator workflow, plus the ``main()`` entry that
parses argv and dispatches to the orchestration helpers in
:mod:`osm_polygon_selection.operations.europe_loop` and
:mod:`osm_polygon_selection.operations.regions`.

Operator scripts (``scripts/operations/*.py``) are thin
launchers that call into these CLI builders.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from osm_polygon_selection.config import RuntimeConfig
from osm_polygon_selection.operations.downloads import pbf_size_mb
from osm_polygon_selection.operations.europe_loop import (
    DEFAULT_EXTRACT_WAIT_S,
    EUROPEAN_COUNTRIES,
    NATURAL_EARTH_SHP,
    complete_stages,
    count_lines,
    download_country_pbf,
    has_extracted,
    is_classified,
    start_extract,
    wait_for_extract,
)
from osm_polygon_selection.operations.regions import (
    COUNTRY_REGIONS,
    DEFAULT_MAX_SECONDS,
    download_region,
    extract_region,
    list_regions,
    resolve_proj,
)


# ---------------------------------------------------------------------------
# scripts/operations/run_europe.py
# ---------------------------------------------------------------------------


def build_run_europe_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Process all European countries end-to-end.",
    )
    parser.add_argument(
        "--max-seconds", type=int, default=DEFAULT_EXTRACT_WAIT_S,
        help=f"Per-country extract wall-clock cap (default {DEFAULT_EXTRACT_WAIT_S})",
    )
    parser.add_argument(
        "--country", type=str, action="append", default=None,
        help="Only process this country (repeatable). Default: all European countries.",
    )
    return parser


def run_europe(argv: list[str] | None = None) -> int:
    """CLI entry for ``scripts/operations/run_europe.py``."""
    args = build_run_europe_parser().parse_args(argv)
    hdd = RuntimeConfig.from_env().data_root
    proc = hdd / "processed"
    raw = hdd / "raw"
    proj = resolve_proj()
    shp = proj / NATURAL_EARTH_SHP

    countries = args.country if args.country else EUROPEAN_COUNTRIES
    pending = [c for c in countries if not is_classified(proc / c)]
    done = [c for c in countries if is_classified(proc / c)]
    print(f"=== Status: {len(done)} done, {len(pending)} pending ===")
    for c in done:
        n = count_lines(proc / c / "03_classified.jsonl")
        print(f"  DONE  {c}: {n}")
    print(f"=== Processing {len(pending)} pending ===")

    for i, country in enumerate(pending, 1):
        print(f"\n[{i}/{len(pending)}] {country}")
        if not has_extracted(proc / country):
            if not download_country_pbf(raw, country):
                print("  download failed, skipping")
                continue
            print(f"  starting extract (will wait up to {args.max_seconds}s)...")
            (proc / country).mkdir(parents=True, exist_ok=True)
            proc_handle = start_extract(
                pbf=raw / f"{country}-latest.osm.pbf",
                dst=proc / country / "01_extracted.jsonl",
                hdd_root=hdd, proj=proj,
            )
            status = wait_for_extract(proc_handle, max_s=args.max_seconds)
            if status == "timeout":
                print("  extract still running, leaving in background")
                continue
            if status == "failed":
                print("  extract failed, skipping")
                continue
            print("  extract done")
        if has_extracted(proc / country):
            n = complete_stages(
                country=country, proc_dir=proc,
                hdd_root=hdd, proj=proj, shp=shp,
            )
            print(f"  -> {n} classified")
    return 0


# ---------------------------------------------------------------------------
# scripts/operations/process_country_regions.py
# ---------------------------------------------------------------------------


def build_process_regions_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Process a country by downloading and extracting regional sub-PBFs.",
    )
    parser.add_argument("country", choices=list(COUNTRY_REGIONS.keys()))
    parser.add_argument(
        "--regions", nargs="*", default=None,
        help="Only process these regions (default: all)",
    )
    parser.add_argument(
        "--skip-download", action="store_true",
        help="Don't download, assume PBFs are already on disk",
    )
    parser.add_argument(
        "--max-seconds", type=int, default=DEFAULT_MAX_SECONDS,
        help=f"Per-region stage 0 wall-clock cap (default {DEFAULT_MAX_SECONDS})",
    )
    return parser


def process_regions(argv: list[str] | None = None) -> int:
    """CLI entry for ``scripts/operations/process_country_regions.py``."""
    args = build_process_regions_parser().parse_args(argv)
    data_root = RuntimeConfig.from_env().data_root
    raw_dir = data_root / "raw"
    proc_dir = data_root / "processed"
    regions = list_regions(args.country, args.regions)
    print(f"Processing {len(regions)} regions for {args.country}")

    for region in regions:
        try:
            if not args.skip_download:
                pbf = download_region(
                    region=region, country=args.country, raw_dir=raw_dir,
                )
            else:
                from osm_polygon_selection.operations.downloads import region_pbf_name
                pbf = raw_dir / region_pbf_name(region)
                if not pbf.exists():
                    print(f"[{region}] PBF not found, skipping")
                    continue
            n = extract_region(
                region=region, pbf=pbf, country=args.country,
                proc_dir=proc_dir, max_seconds=args.max_seconds,
            )
            print(f"[{region}] {n:,} polygons", flush=True)
        except Exception as e:
            print(f"[{region}] FAILED: {e}")
    return 0


__all__ = [
    "build_process_regions_parser",
    "build_run_europe_parser",
    "process_regions",
    "run_europe",
]

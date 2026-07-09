"""Process a country by downloading and processing regional sub-PBFs.

Used for large countries (france, germany) where the full PBF is too
big to process in the agent runtime. Geofabrik publishes regional
sub-PBFs (e.g. alsace, bretagne, ile-de-france) that are 10-100x
smaller. This script downloads them, runs stage 0 on each, and
merges the resulting 01_extracted.jsonl files into the main
country output.

Each regional PBF processes in a few minutes, yielding 10k-100k
polygons. Together they cover the whole country.

Env vars:
- ``OSM_DATA_ROOT``: maintainer HDD root. Default: sibling-of-repo
  ``osm-polygon-selection`` (via ``RuntimeConfig``).
- ``OSM_REPO_ROOT``: project root for ``cwd`` of stage 0 subprocess.
  Default: ``Path.cwd().resolve()``.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from osm_polygon_selection.runtime_config import RuntimeConfig

DATA_ROOT = RuntimeConfig.from_env().data_root
RAW_DIR = DATA_ROOT / "raw"
PROCESSED_DIR = DATA_ROOT / "processed"


def download(region: str, pbf_url: str) -> Path:
    """Download a regional PBF if not already on disk. Returns path."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    pbf = RAW_DIR / f"{region}-latest.osm.pbf"
    if pbf.exists() and pbf.stat().st_size > 1024 * 1024:
        print(f"[{region}] already on disk: {pbf}")
        return pbf
    print(f"[{region}] downloading from {pbf_url} ...")
    subprocess.run(
        ["curl", "-L", "-s", "-o", str(pbf), pbf_url],
        check=True,
    )
    sz_mb = pbf.stat().st_size / 1024 / 1024
    print(f"[{region}] downloaded {sz_mb:.1f}MB")
    return pbf


def extract_region(region: str, pbf: Path, country: str, max_seconds: int = 600) -> int:
    """Run stage 0 on a regional PBF.

    Each region writes to its own per-region output file
    (01_extracted_<region>.jsonl) so multiple regions can run
    in parallel without clobbering each other's WAL.

    Returns the number of polygons in the per-region output.
    """
    country_dir = PROCESSED_DIR / country
    country_dir.mkdir(parents=True, exist_ok=True)
    out = country_dir / f"01_extracted_{region}.jsonl"
    print(f"[{region}] extracting to {out.name} ...", flush=True)
    repo_root = Path(os.environ.get("OSM_REPO_ROOT", Path.cwd().resolve()))
    subprocess.run(
        [
            "uv", "run", "scripts/stage0_extract.py",
            str(pbf), str(out),
            "--max-seconds", str(max_seconds),
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    n = 0
    if out.exists():
        n = sum(1 for _ in out.open())
    print(f"[{region}] {n:,} polygons", flush=True)
    return n


# Map of country -> [(region, pbf_path_relative)]
# Populated at runtime via --regions arg
COUNTRY_REGIONS = {
    "france": [
        "alsace", "aquitaine", "auvergne", "basse-normandie", "bourgogne",
        "bretagne", "centre", "champagne-ardenne", "corse", "franche-comte",
        "guadeloupe", "guyane", "haute-normandie", "ile-de-france",
        "languedoc-roussillon", "limousin", "lorraine", "martinique",
        "mayotte", "midi-pyrenees", "nord-pas-de-calais", "pays-de-la-loire",
        "picardie", "poitou-charentes", "provence-alpes-cote-d-azur",
        "reunion", "rhone-alpes",
    ],
    "germany": [
        "baden-wuerttemberg", "bayern", "berlin", "brandenburg", "bremen",
        "hamburg", "hessen", "mecklenburg-vorpommern", "niedersachsen",
        "nordrhein-westfalen", "rheinland-pfalz", "saarland", "sachsen",
        "sachsen-anhalt", "schleswig-holstein", "thueringen",
    ],
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("country", choices=list(COUNTRY_REGIONS.keys()))
    parser.add_argument(
        "--regions", nargs="*", default=None,
        help="Only process these regions (default: all)",
    )
    parser.add_argument(
        "--skip-download", action="store_true",
        help="Don't download, assume PBFs are already on disk",
    )
    args = parser.parse_args()

    regions = args.regions or COUNTRY_REGIONS[args.country]
    print(f"Processing {len(regions)} regions for {args.country}")

    for region in regions:
        pbf_name = f"{region}-latest.osm.pbf"
        if not args.skip_download:
            pbf_url = (
                f"https://download.geofabrik.de/europe/{args.country}/{pbf_name}"
            )
            pbf = download(region, pbf_url)
        else:
            pbf = RAW_DIR / pbf_name
            if not pbf.exists():
                print(f"[{region}] PBF not found, skipping")
                continue

        try:
            extract_region(region, pbf, args.country)
        except Exception as e:
            print(f"[{region}] FAILED: {e}")


if __name__ == "__main__":
    main()
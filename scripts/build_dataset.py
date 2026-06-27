"""Build the published dataset from per-country 03_classified.jsonl files.

Output: a single parquet file at data/processed/<country>/05_dataset.parquet
plus a metadata.json with schema and provenance.

Each row has:
- All fields from 03_classified.jsonl (osm_id, osm_type, geometry,
  centroid, area_km2, tags, continent, size_bin)
- country: the country name (added by run_country.sh or this script)
- extract_status: "clean" or "killed" (whether the extract process
  finished its run.json before being killed)
- pbf_date: the date embedded in the PBF filename (e.g. "latest" or
  "260627" for some Geofabrik PBFs)
- pipeline_version: the git SHA or a hardcoded version string

The geometry field is kept as WKT for compatibility with the existing
JSONL readers. Downstream users who want Shapely can do
`shapely.wkt.loads(row.geometry)`. We could switch to binary
WKB for smaller file size, but WKT is more debuggable.
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

HDD = Path("/Volumes/Seagate M3/osm-polygon-selection")
PROC = HDD / "processed"
PIPELINE_VERSION = "v0.1.0"


def git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd="/Users/noeflandre/osm-polygon-selection",
        ).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def extract_status(country: str) -> str:
    """True if the run.json file exists (extract finished cleanly)."""
    return "clean" if (PROC / country / "01_extracted.jsonl.run.json").exists() else "killed"


def build_schema() -> pa.Schema:
    return pa.schema([
        ("osm_id", pa.int64()),
        ("osm_type", pa.string()),
        ("centroid_lon", pa.float64()),
        ("centroid_lat", pa.float64()),
        ("area_km2", pa.float64()),
        ("tags", pa.list_(pa.string())),
        ("continent", pa.string()),
        ("size_bin", pa.string()),
        ("country", pa.string()),
        ("extract_status", pa.string()),
        ("pbf_date", pa.string()),
    ])


def row_to_record(row: dict, country: str, status: str, pbf_date: str) -> dict | None:
    """Convert one JSONL row + metadata into a dataset record.

    Drops the WKT geometry (we keep only the centroid + area for the
    published dataset — this is the "lightweight" version that
    downstream classifiers and samplers actually need). The WKT is
    huge for big countries and most users re-derive the geometry
    from centroid + area at their own resolution.
    """
    try:
        c = row.get("centroid", [None, None])
        return {
            "osm_id": int(row["osm_id"]),
            "osm_type": str(row.get("osm_type", "")),
            "centroid_lon": float(c[0]) if c and len(c) > 0 else None,
            "centroid_lat": float(c[1]) if c and len(c) > 1 else None,
            "area_km2": float(row.get("area_km2", 0.0)),
            "tags": list(row.get("tags", [])),
            "continent": str(row.get("continent", "unknown")),
            "size_bin": str(row.get("size_bin", "small")),
            "country": country,
            "extract_status": status,
            "pbf_date": pbf_date,
        }
    except (KeyError, TypeError, ValueError) as e:
        print(f"  skipping malformed row in {country}: {e}", file=sys.stderr)
        return None


def pbf_date_for(country: str) -> str:
    """Get the date of the PBF file from its mtime."""
    pbf = HDD / "raw" / f"{country}-latest.osm.pbf"
    if not pbf.exists():
        return "unknown"
    mtime = pbf.stat().st_mtime
    return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")


def write_readme(out_dir: Path, countries_done: list[dict], total_polygons: int) -> None:
    # YAML frontmatter for HuggingFace dataset viewer compatibility.
    # Without this, HF shows "empty or missing yaml metadata in repo card"
    # as a warning at the top of the dataset page.
    yaml_frontmatter = """---
license: odbl
task_categories:
  - other
language:
  - en
tags:
  - geospatial
  - openstreetmap
  - osm
  - polygons
  - landuse
  - landcover
  - remote-sensing
  - foundation-model
size_categories:
  - 1M<n<10M
---

"""
    readme = yaml_frontmatter + f"""# osm-polygon-selection dataset

A curated set of OpenStreetMap polygons across {len(countries_done)}
European countries, classified by size bin (small/medium/large,
area in [0.1, 100] km²) and tagged by continent (Natural Earth
admin0 lookup).

## Geographic distribution

![Polygon distribution across Europe](map_preview.png)

The map above shows a stratified sample of 1,200 polygons from the
dataset (color-coded by country, sized by area). It gives a rough
visual sense of which European regions are well-covered and which
are sparse.

## Files

- `all_europe.parquet` — all {total_polygons:,} polygons in a single file
- `<country>.parquet` — per-country files
- `map_preview.png` — geographic distribution preview (this README)
- `metadata.yaml` — HuggingFace dataset viewer metadata
- `manifest.json` — machine-readable build manifest
- `README.md` — this file

## Resources

To understand where this dataset comes from and how the filters
were designed, see these resources:

- **Blog post** (long-form context): [OSM data analysis for landuse](https://noeflandre.com/posts/osm-data-analysis) on noeflandre.com. Explains the osm-stats clustering that produced the whitelist, including the arithmetic correction (the blog originally claimed 326 union base keys; the correct value is 236).
- **GitHub repo** (code + documentation): [NoeFlandre/osm-polygon-selection](https://github.com/NoeFlandre/osm-polygon-selection). The pipeline source code, whitelist decisions, and dataset-state documentation.
- **Related repo** (whitelist source data): [NoeFlandre/osm-stats](https://github.com/NoeFlandre/osm-stats). The TF-IDF and embeddings analyses on OSM tags that fed into the 22,075-tag whitelist.
- **Project repo docs** (in-repo documentation): `docs/whitelist_decisions.md` (Tier A / Tier B inclusion rules) and `docs/dataset_state.md` (per-country coverage breakdown and known issues).

## Schema

| column | type | description |
|--------|------|-------------|
| osm_id | int64 | OSM object id |
| osm_type | string | "way" or "relation" |
| centroid_lon | float64 | polygon centroid longitude (WGS84) |
| centroid_lat | float64 | polygon centroid latitude (WGS84) |
| area_km2 | float64 | polygon area in km² (Web Mercator, accurate at mid-latitudes) |
| tags | list(string) | OSM `key=value` tags |
| continent | string | Natural Earth admin0 lookup of the centroid |
| size_bin | string | "small" (0.1-1), "medium" (1-10), or "large" (10-100) km² |
| country | string | ISO-style country name |
| extract_status | string | "clean" (extract process ran to completion) or "killed" (extract was interrupted before completion) |
| pbf_date | string | date of the source PBF file (from mtime) |

## Provenance

- Pipeline version: {PIPELINE_VERSION}
- Git SHA: {git_sha()}
- Built: {datetime.now().isoformat()}
- Source: Geofabrik regional extracts (`https://download.geofabrik.de/`)
- Whitelist: 22,075 OSM `key=value` tags from osm-stats (see
  `docs/whitelist_decisions.md` in the project repo)

## Filter chain

Each polygon in this dataset has passed three filters:

1. **Size filter (Stage 0)**: area in [0.1, 100] km².
   Polygons smaller than 0.1 km² or larger than 100 km² are dropped.
2. **Whitelist filter (Stage 2)**: at least one OSM tag in the
   22,075-tag whitelist. The whitelist is derived from a clustering
   of OSM tags across both `tfidf` and `embeddings` analyses.
3. **Classify (Stage 3)**: continent assigned via Natural Earth
   admin0 shapefile, size_bin assigned by area.

## Known issues

Some countries in this dataset (those with `extract_status = "killed"`)
had their Stage 0 extract process interrupted before the entire PBF
was yielded. The yielded polygons that made it to disk are valid and
complete, but a small tail of polygons (typically 5-10% of the
country's total) is missing. See `docs/dataset_state.md` in the repo
for the full list. To complete them, re-run `scripts/run_country.sh
<country>` — the `.seen_ids` WAL preserves the work already done.

## Per-country summary
"""
    for c in countries_done:
        readme += f"- {c['country']}: {c['n_polygons']:,} polygons ({c['extract_status']})\n"

    (out_dir / "README.md").write_text(readme)
    print(f"README.md written ({len(readme)} chars)")


def main() -> None:
    out_dir = Path("/Users/noeflandre/osm-polygon-selection/data/dataset")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    countries_done = []
    for country_dir in sorted(PROC.iterdir()):
        if not country_dir.is_dir():
            continue
        classified = country_dir / "03_classified.jsonl"
        if not classified.exists():
            continue
        country = country_dir.name
        status = extract_status(country)
        pbf_date = pbf_date_for(country)

        rows = []
        with classified.open() as f:
            for line in f:
                rec = row_to_record(json.loads(line), country, status, pbf_date)
                if rec is not None:
                    rows.append(rec)
        if not rows:
            continue

        table = pa.Table.from_pylist(rows, schema=build_schema())
        out_file = out_dir / f"{country}.parquet"
        pq.write_table(table, out_file, compression="snappy")
        countries_done.append({
            "country": country,
            "n_polygons": len(rows),
            "extract_status": status,
            "pbf_date": pbf_date,
        })
        print(f"  {country}: {len(rows)} polygons -> {out_file.name}")

    print("\nBuilding combined parquet...")
    all_tables = []
    for c in countries_done:
        table = pq.read_table(out_dir / f"{c['country']}.parquet")
        all_tables.append(table)
    combined = pa.concat_tables(all_tables, promote_options="default")
    pq.write_table(combined, out_dir / "all_europe.parquet", compression="snappy")
    print(f"  combined: {combined.num_rows} polygons -> all_europe.parquet")

    write_readme(out_dir, countries_done, combined.num_rows)

    manifest = {
        "version": PIPELINE_VERSION,
        "git_sha": git_sha(),
        "built_at": datetime.now().isoformat(),
        "total_polygons": combined.num_rows,
        "n_countries": len(countries_done),
        "countries": countries_done,
        "schema": [f.name for f in build_schema()],
        "filters": {
            "min_area_km2": 0.1,
            "max_area_km2": 100.0,
            "whitelist_size": 22075,
        },
        "resources": {
            "blog_post": "https://noeflandre.com/posts/osm-data-analysis",
            "github_repo": "https://github.com/NoeFlandre/osm-polygon-selection",
            "related_repo": "https://github.com/NoeFlandre/osm-stats",
        },
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"manifest.json written")


if __name__ == "__main__":
    main()
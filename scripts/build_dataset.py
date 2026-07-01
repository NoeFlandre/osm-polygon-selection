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

Geometry: INCLUDED by default. Each row keeps the full polygon WKT
(Or WKB if OSM_POLYGON_GEOMETRY=wkb) so downstream users can render
the polygon, query it spatially, etc. without re-deriving it from
centroid + area. The 03_classified.jsonl input already has the WKT
in row["geometry"]; we just pipe it through.

Format controlled by the OSM_POLYGON_GEOMETRY env var:

  OSM_POLYGON_GEOMETRY=wkt    (default) - keep geometry as WKT (text)
  OSM_POLYGON_GEOMETRY=wkb    - keep geometry as WKB (binary, ~50% smaller)
  OSM_POLYGON_GEOMETRY=none  - drop geometry (centroid + area only)
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

# Dataset output directory. The default is data/dataset on the
# project repo (good for git diffs and the small per-country
# parquets). But the combined all_europe.parquet is 4+GB when
# geometry is included, and the project repo lives on the
# internal SSD (228GB, often near full). Override with the
# OSM_DATASET_DIR env var to point at the external HDD.
_default_dataset_dir = Path(__file__).resolve().parent.parent / "data" / "dataset"
DATASET_DIR = Path(os.environ.get("OSM_DATASET_DIR", str(_default_dataset_dir)))

# Geometry encoding: wkt (default, text), wkb (binary, ~50% smaller),
# or none (drop entirely, just keep centroid + area).
GEOMETRY_ENCODING = os.environ.get("OSM_POLYGON_GEOMETRY", "wkt").lower()
if GEOMETRY_ENCODING not in ("wkt", "wkb", "none"):
    raise SystemExit(
        f"OSM_POLYGON_GEOMETRY must be wkt, wkb, or none; got {GEOMETRY_ENCODING!r}"
    )


def git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd="/Users/noeflandre/osm-polygon-selection",
        ).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def extract_status(country: str) -> str:
    """True if at least one extract run finished (extract process reached end).

    For countries processed via regional sub-PBFs, each sub-region has
    its own `01_extracted_<region>.jsonl.run.json`. We accept the
    country as "clean" if EITHER the merged run.json exists OR any
    sub-region run.json exists (i.e., at least one extract finished).
    """
    country_dir = PROC / country
    if (country_dir / "01_extracted.jsonl.run.json").exists():
        return "clean"
    for p in country_dir.glob("01_extracted_*.jsonl.run.json"):
        return "clean"
    return "killed"


def build_schema() -> pa.Schema:
    fields = [
        ("osm_id", pa.int64()),
        ("osm_type", pa.string()),
        ("centroid_lon", pa.float64()),
        ("centroid_lat", pa.float64()),
        ("area_km2", pa.float64()),
        ("tags", pa.list_(pa.string())),
        ("matched_tag", pa.string()),
        ("continent", pa.string()),
        ("size_bin", pa.string()),
        ("country", pa.string()),
        ("extract_status", pa.string()),
        ("pbf_date", pa.string()),
    ]
    if GEOMETRY_ENCODING == "wkt":
        fields.append(("geometry_wkt", pa.string()))
    elif GEOMETRY_ENCODING == "wkb":
        fields.append(("geometry_wkb", pa.binary()))
    # GEOMETRY_ENCODING == "none" → no geometry column
    return pa.schema(fields)


def _encode_geometry(row: dict) -> bytes | str | None:
    """Extract geometry from the row in the chosen encoding.

    The 03_classified.jsonl input has the WKT in row["geometry"] (a
    string from shapely.wkt on the original PBF). We pipe it through
    as-is for "wkt", or convert to WKB for "wkb". For "none", we
    return None and the field is dropped.
    """
    wkt = row.get("geometry")
    if not wkt or GEOMETRY_ENCODING == "none":
        return None
    if GEOMETRY_ENCODING == "wkt":
        return wkt
    # WKB: parse the WKT and serialize to binary.
    import shapely.wkt as _shapely_wkt
    geom = _shapely_wkt.loads(wkt)
    return geom.wkb


def _load_whitelist() -> set[str]:
    """Load the 22,075-tag whitelist used by Stage 2.

    Cached at module level so we only hit the disk once per build.
    """
    global _WHITELIST_CACHE
    if _WHITELIST_CACHE is None:
        with (HDD / "whitelist.json").open() as f:
            _WHITELIST_CACHE = set(json.load(f))
    return _WHITELIST_CACHE


_WHITELIST_CACHE: set[str] | None = None


def _compute_matched_tag(row: dict) -> str:
    """Return the first tag in row.tags that hits the whitelist.

    Older 03_classified.jsonl files (pre-matched_tag) don't have this
    field, so we compute it from row.tags at build time. This avoids
    re-running Stage 2 across all countries just to backfill the
    column.
    """
    mt = row.get("matched_tag")
    if mt:
        return str(mt)
    wl = _load_whitelist()
    for t in row.get("tags", []):
        if t in wl:
            return str(t)
    return ""


def row_to_record(row: dict, country: str, status: str, pbf_date: str) -> dict | None:
    """Convert one JSONL row + metadata into a dataset record.

    Each row keeps the polygon geometry (per OSM_POLYGON_GEOMETRY
    env var) plus centroid + area + tags. The geometry column is
    named "geometry_wkt" (text) or "geometry_wkb" (binary).

    The `matched_tag` column captures the whitelist tag that kept
    this polygon. For countries whose 03_classified.jsonl was built
    before this column existed, we compute it at build time from
    the row's tags against the whitelist (no re-running Stage 2).
    """
    try:
        c = row.get("centroid", [None, None])
        rec = {
            "osm_id": int(row["osm_id"]),
            "osm_type": str(row.get("osm_type", "")),
            "centroid_lon": float(c[0]) if c and len(c) > 0 else None,
            "centroid_lat": float(c[1]) if c and len(c) > 1 else None,
            "area_km2": float(row.get("area_km2", 0.0)),
            "tags": list(row.get("tags", [])),
            "matched_tag": _compute_matched_tag(row),
            "continent": str(row.get("continent", "unknown")),
            "size_bin": str(row.get("size_bin", "small")),
            "country": country,
            "extract_status": status,
            "pbf_date": pbf_date,
        }
        geom = _encode_geometry(row)
        if GEOMETRY_ENCODING == "wkt":
            rec["geometry_wkt"] = geom
        elif GEOMETRY_ENCODING == "wkb":
            rec["geometry_wkb"] = geom
        return rec
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


def write_metadata_yaml(out_dir: Path) -> None:
    """Write metadata.yaml for the HuggingFace dataset viewer.

    Same fields as the YAML frontmatter in the README. HF accepts
    both, but having a standalone file makes the metadata visible
    even before the README is parsed.
    """
    yaml_content = """license: odbl
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
"""
    (out_dir / "metadata.yaml").write_text(yaml_content)
    print("metadata.yaml written")


def build_country_table(countries: list[dict]) -> str:
    """Render the per-country summary as a markdown table.

    Pure function: takes the same `countries_done` list-of-dicts
    that's already produced by `main()` (each entry has at least
    `country`, `n_polygons`, and `extract_status`) and returns a
    markdown table string.

    Columns: Country | Polygons | Status

    Rows are sorted alphabetically by country name so the output is
    deterministic. A grand-total row is appended at the bottom.

    Countries with `extract_status='killed'` are NOT filtered out —
    they appear with status='killed' so the manifest is complete.
    """
    header = "| Country | Polygons | Status |\n|---------|----------|--------|"
    rows = sorted(countries, key=lambda c: c["country"])
    lines = [header]
    for c in rows:
        lines.append(
            f"| {c['country']} | {c['n_polygons']:,} | {c['extract_status']} |"
        )
    total = sum(c["n_polygons"] for c in countries)
    lines.append(f"| **Total** | {total:,} | |")
    return "\n".join(lines)


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
    # Count clean vs killed to give an accurate status line.
    n_clean = sum(1 for c in countries_done if c["extract_status"] == "clean")
    n_killed = sum(1 for c in countries_done if c["extract_status"] == "killed")
    if n_killed == 0:
        status_line = (
            f"All {n_clean} countries are extracted end-to-end "
            f"(every OSM object examined, `run.json` written). "
            f"No country was killed mid-pipeline."
        )
    else:
        status_line = (
            f"{n_clean} of {len(countries_done)} countries are clean. "
            f"{n_killed} country(ies) were killed mid-pipeline — see 'Known issues' below."
        )

    # Schema description table. Includes geometry if it's included
    # in the dataset. The columns list is built from build_schema() so
    # it's always in sync with what the parquet actually contains.
    schema_columns = [
        ("osm_id", "int64", "OSM object id"),
        ("osm_type", "string", '"way" or "relation"'),
        ("centroid_lon", "float64", "polygon centroid longitude (WGS84)"),
        ("centroid_lat", "float64", "polygon centroid latitude (WGS84)"),
        ("area_km2", "float64", "polygon area in km² (Web Mercator, accurate at mid-latitudes)"),
        ("tags", "list(string)", "OSM `key=value` tags"),
        ("matched_tag", "string", "the first tag in `tags` that hit the whitelist filter (the reason the polygon survived)"),
        ("continent", "string", "Natural Earth admin0 lookup of the centroid"),
        ("size_bin", "string", '"small" (0.1-1), "medium" (1-10), or "large" (10-100) km²'),
        ("country", "string", "ISO-style country name"),
        ("extract_status", "string", '"clean" (extract process ran to completion) or "killed" (extract was interrupted before completion)'),
        ("pbf_date", "string", "date of the source PBF file (from mtime)"),
    ]
    if GEOMETRY_ENCODING == "wkt":
        schema_columns.append((
            "geometry_wkt", "string",
            "**polygon geometry as WKT** (WGS84, well-known text). "
            "Parse with `shapely.wkt.loads(row.geometry_wkt)`. "
            "Default encoding; size of the combined parquet scales "
            "with polygon complexity (~3-5x larger than centroid-only)."
        ))
    elif GEOMETRY_ENCODING == "wkb":
        schema_columns.append((
            "geometry_wkb", "binary",
            "**polygon geometry as WKB** (WGS84, well-known binary). "
            "Parse with `shapely.wkt.loads(row.geometry_wkb)`. "
            "Smaller than WKT (~50% smaller) at the cost of being binary."
        ))
    # GEOMETRY_ENCODING == "none" → no geometry column

    schema_table = "| column | type | description |\n|--------|------|-------------|\n"
    for name, dtype, desc in schema_columns:
        schema_table += f"| {name} | {dtype} | {desc} |\n"

    readme = yaml_frontmatter + f"""# osm-polygon-selection dataset

A curated set of OpenStreetMap polygons across {len(countries_done)}
European countries, classified by size bin (small/medium/large,
area in [0.1, 100] km²) and tagged by continent (Natural Earth
admin0 lookup).

**Status:** {status_line}

**Total polygons:** {sum(c['n_polygons'] for c in countries_done):,}
(combined parquet: `all_europe.parquet`).

## What's in this dataset

Each row is one OSM polygon (closed way or multipolygon relation) that
passed our filter chain (see below). The polygon **geometry itself**
is included in the row as WKT (or WKB if `OSM_POLYGON_GEOMETRY=wkb`
is set when the dataset is built) so you can render, query, or
reproject it directly without re-deriving from centroid+area.

{schema_table}

## Provenance

- Pipeline version: {PIPELINE_VERSION}
- Git SHA: {git_sha()}
- Built: {datetime.now().isoformat()}
- Source: Geofabrik regional extracts (`https://download.geofabrik.de/`)
- Whitelist: 22,075 OSM `key=value` tags from osm-stats (see
  `docs/whitelist_decisions.md` in the project repo)

## Geographic distribution

![polygon distribution across Europe](map_preview.png)

(Each circle is one polygon, color-coded by country. Circle size is
proportional to `sqrt(area_km2)`.)

## Filter chain

Each polygon in this dataset has passed three filters:

1. **Size filter (Stage 0)**: area in [0.1, 100] km².
   Polygons smaller than 0.1 km² or larger than 100 km² are dropped.
2. **Whitelist filter (Stage 2)**: at least one OSM tag in the
   22,075-tag whitelist. The whitelist is derived from a clustering
   of OSM tags across both `tfidf` and `embeddings` analyses.
3. **Classify (Stage 3)**: continent assigned via Natural Earth
   admin0 shapefile, size_bin assigned by area.

## Per-country summary

{build_country_table(countries_done)}
"""

    (out_dir / "README.md").write_text(readme)
    print(f"README.md written ({len(readme)} chars)")


def main() -> None:
    out_dir = DATASET_DIR
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # First pass: countries with a non-empty 03_classified.jsonl.
    # These produce per-country parquet files + manifest rows.
    # IMPORTANT: only consider direct subdirectories of PROC as
    # countries. Per-region subdirectories inside a country (e.g.
    # processed/france/alsace/ from regional processing) are
    # NOT countries — they are subsets of the parent country.
    countries_done = []
    for country_dir in sorted(PROC.iterdir()):
        if not country_dir.is_dir():
            continue
        # Skip subdirectories that live inside another country
        # directory. processed/<country>/<region>/... is the regional
        # layout; those are not independent countries.
        if country_dir.parent != PROC:
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
            # Zero-yield 03_classified.jsonl: country attempted, extract ran
            # but produced no polygons (e.g. killed before any output).
            # Record it in the manifest with n_polygons=0 so downstream
            # users know the country was tried but is absent from the data.
            countries_done.append({
                "country": country,
                "n_polygons": 0,
                "extract_status": status,  # "killed" if run.json missing
                "pbf_date": pbf_date,
            })
            print(f"  {country}: 0 polygons (zero-yield, recorded in manifest only)")
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

    # Second pass: countries that have a raw/ PBF but no 03_classified.jsonl
    # at all (i.e. Stage 0 was started but killed before reaching Stage 2/3).
    # Excludes the continent-wide "europe-latest.osm.pbf" (the parent
    # Geofabrik extract, not a country).
    # Also excludes regional sub-PBFs of large countries (e.g. alsace,
    # aquitaine for france) — those are subsets of their parent
    # country, not independent countries.
    raw_dir = HDD / "raw"
    # Countries that have a parent PBF in raw/ but are processed via
    # regional sub-PBFs. Add new ones here as we go.
    REGIONAL_CHILDREN = {
        "france": {
            "alsace", "aquitaine", "auvergne", "basse-normandie", "bourgogne",
            "bretagne", "centre", "champagne-ardenne", "corse", "franche-comte",
            "guadeloupe", "guyane", "haute-normandie", "ile-de-france",
            "languedoc-roussillon", "limousin", "lorraine", "martinique",
            "mayotte", "midi-pyrenees", "nord-pas-de-calais", "pays-de-la-loire",
            "picardie", "poitou-charentes", "provence-alpes-cote-d-azur",
            "reunion", "rhone-alpes",
        },
        "germany": {
            "baden-wuerttemberg", "bayern", "berlin", "brandenburg", "bremen",
            "hamburg", "hessen", "mecklenburg-vorpommern", "niedersachsen",
            "nordrhein-westfalen", "rheinland-pfalz", "saarland", "sachsen",
            "sachsen-anhalt", "schleswig-holstein", "thueringen",
        },
        "norway": {
            "nord-norge", "ostlandet", "sorlandet", "svalbard-janmayen",
            "trondelag", "vestlandet",
        },
        "italy": {
            "centro", "isole", "nord-est", "nord-ovest", "sud",
        },
        "netherlands": {
            "drenthe", "flevoland", "friesland", "gelderland", "groningen",
            "limburg", "noord-brabant", "noord-holland", "overijssel",
            "utrecht", "zeeland", "zuid-holland",
        },
        "poland": {
            "dolnoslaskie", "kujawsko-pomorskie", "lodzkie", "lubelskie",
            "lubuskie", "malopolskie", "mazowieckie", "opolskie",
            "podkarpackie", "podlaskie", "pomorskie", "slaskie",
            "swietokrzyskie", "warminsko-mazurskie", "wielkopolskie",
            "zachodniopomorskie",
        },
        "spain": {
            "andalucia", "aragon", "asturias", "cantabria",
            "castilla-la-mancha", "castilla-y-leon", "cataluna", "ceuta",
            "extremadura", "galicia", "islas-baleares", "la-rioja",
            "madrid", "melilla", "murcia", "navarra", "pais-vasco",
            "valencia",
        },
        "united-kingdom": {
            "england", "scotland", "wales", "bermuda", "falklands",
        },
    }
    # All regional children across all countries
    ALL_REGIONAL = set()
    for children in REGIONAL_CHILDREN.values():
        ALL_REGIONAL.update(children)

    for pbf in sorted(raw_dir.glob("*-latest.osm.pbf")):
        country = pbf.name.replace("-latest.osm.pbf", "")
        if country == "europe":
            continue
        if country in ALL_REGIONAL:
            # Sub-region of a larger country; not an independent country.
            continue
        if any(c["country"] == country for c in countries_done):
            continue
        countries_done.append({
            "country": country,
            "n_polygons": 0,
            "extract_status": "killed",
            "pbf_date": datetime.fromtimestamp(pbf.stat().st_mtime).strftime("%Y-%m-%d"),
        })
        print(f"  {country}: 0 polygons (no 03 file, PBF present, recorded)")
    print("\nBuilding combined parquet...")
    all_tables = []
    for c in countries_done:
        # Skip zero-yield countries: they have no per-country parquet file.
        if c["n_polygons"] == 0:
            continue
        table = pq.read_table(out_dir / f"{c['country']}.parquet")
        all_tables.append(table)
    combined = pa.concat_tables(all_tables, promote_options="default")
    # Write the combined parquet to the same directory as the
    # per-country ones. If geometry is included, this can be 4-5GB
    # and won't fit on the internal SSD (228GB, often near full).
    # The data/ directory on the internal drive is fine for the
    # small per-country files; for the combined file, we honor
    # the OSM_DATASET_DIR env var if set (used by the agent to
    # point at the external HDD when space is tight).
    out_path = out_dir / "all_europe.parquet"
    print(f"  combined: {combined.num_rows} polygons -> {out_path}")
    pq.write_table(combined, out_path, compression="snappy")

    write_readme(out_dir, countries_done, combined.num_rows)
    write_metadata_yaml(out_dir)

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
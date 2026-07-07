"""Organize the published HF dataset into a public-facing subfolder layout.

Takes the flat ``dataset/`` directory (per-country parquets at the root,
combined ``all_world.parquet`` at the root, ``map_preview.png`` at the
root, sample_map.jsonl in /tmp) and reorganizes it into:

    dataset/
    ├── README.md, manifest.json, metadata.yaml       (landing page)
    ├── per_country/<country>/{README.md, <country>.parquet}
    ├── combined/{README.md, all_world.parquet}
    ├── sample/{README.md, sample_map.jsonl}
    └── preview/{README.md, map_preview.png}

Each leaf folder gets a README.md so HuggingFace can use it as the
folder description (no empty folders).

The script is intentionally split into small pure functions so each
step can be unit-tested and re-run independently. Running it twice is
safe: every move is a no-op if the file is already at the destination,
and every README write is idempotent.

CLI:

    uv run python scripts/organize_dataset.py [--root PATH]

The default ``--root`` is ``/Volumes/Seagate M3/osm-polygon-selection/dataset``
(the same location ``build_dataset.py`` writes to when ``OSM_DATASET_DIR``
points at the external HDD).
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path

from osm_polygon_selection.country_table import build_country_table
from osm_polygon_selection.dataset_layout import (
    SUBFOLDERS,
    cleanup_loose_root_files,
    ensure_layout,
    move_combined,
    move_country_files,
    move_preview,
    move_sample,
)
from osm_polygon_selection.pbf_meta import geofabrik_url
from osm_polygon_selection.pbf_meta import NON_EUROPE_COUNTRIES as _NON_EUROPE
from osm_polygon_selection.readme_render import (
    PIPELINE_VERSION_DEFAULT,
    build_country_readme,
    build_folder_readme,
    write_metadata_yaml,
)
from osm_polygon_selection.sample_table import build_example_row_table
from osm_polygon_selection.country_notes import (
    country_note,
    country_source_description,
)


DEFAULT_ROOT = Path("/Volumes/Seagate M3/osm-polygon-selection/dataset")

# ---------------------------------------------------------------------------
# Templates (one place to edit prose; module-level constants)
# ---------------------------------------------------------------------------

_COUNTRY_README_TEMPLATE = """# {country}

{n_polygons:,} polygons from `{country}-latest.osm.pbf` on Geofabrik
([source]({geofabrik_url})), filtered by the
[22,075-tag whitelist](https://github.com/NoeFlandre/osm-stats) and
classified by continent + size bin.

| field | value |
|-------|-------|
| country | `{country}` |
| polygons | **{n_polygons:,}** |
| extract_status | **{extract_status}** |
| pbf_date | {pbf_date} |
| source | {source_description} |
| Geofabrik extract | <{geofabrik_url}> |

## Geometry

The parquet file in this folder
(`{country}.parquet`) has the same schema as the combined
`combined/all_world.parquet`. Each row carries the polygon
**geometry as WKT** (default), plus centroid + area + the
whitelist-matched tag.

Load with:

```python
import pyarrow.parquet as pq
table = pq.read_table("per_country/{country}/{country}.parquet")
df = table.to_pandas()
# df["geometry_wkt"] is a column of WKT strings; parse with shapely.wkt.loads
```

## Notes

{note}
"""

_PER_COUNTRY_README_TEMPLATE = """# per_country/

**{n_country_folders} country folders** (one per country),
each containing one `<country>.parquet` file and one `README.md`.
Total polygons across all countries: **{total_polygons:,}**.

The per-country split mirrors Geofabrik's regional extracts.
Use this folder when you want a single country without paying for
the full ~13 GB combined file.
Each parquet has the same 13-column schema as
[`../combined/all_world.parquet`](../combined/all_world.parquet).

For the all-in-one file, see [`../combined/`](../combined/). For a
small representative sample ({sample_n_polygons:,} polygons, one per
~1.7k), see [`../sample/`](../sample/). For a thumbnail of the
geographic distribution, see [`../preview/`](../preview/).

[Back to the dataset root](../README.md)
"""

_COMBINED_README_TEMPLATE = """# combined/

**1 file**: `all_world.parquet` — a single parquet with **every**
polygon from **every** country concatenated.

**{n_rows:,} polygons** across **{n_countries} countries and
sub-country regions** ({size_human}). Schema is identical to the
per-country parquets. Built from the per-country parquet files in
[`../per_country/`](../per_country/). The `country` column tells you
which country each row came from.

The parquet is written with small row groups (~50k rows each, ~50 MB
per group) so the HuggingFace dataset viewer can scan one row group
at a time without exceeding its 300 MB scan limit.

[Back to the dataset root](../README.md)
"""

_SAMPLE_README_TEMPLATE = """# sample/

**1 file**: `sample_map.jsonl` — a **{n_rows:,}-polygon** spatial
sample of the full worldwide dataset, designed to be **highly
representative** of the geographic distribution without being too
dense to render in a browser. Use it as a quick look at "what does
this dataset look like?" without downloading the 13 GB combined
parquet. Schema is centroid-only (no geometry column).

Generated by `scripts/sample_for_map.py`. Algorithm:

1. **Power-law per-country allocation**: each country gets
   `clamp(round(n_polygons ** 0.4), 8, 200)` polygons. This compresses
   the per-country range so dense countries (germany: 1.1M) don't crowd
   out sparse ones (monaco: 2), while still preserving the relative
   density differences.
2. **Spatial coverage within each country**: each polygon's centroid is
   bucketed into a `K x K` grid (`K = ceil(sqrt(target_n))`), then one
   random polygon per cell is kept. This avoids clustering in dense
   regions and ensures the sampled polygons are well-spread.
3. **Floor of 8** so even monaco's 2 polygons are visible.
4. **Cap of 200** so germany doesn't fill the map.

The same sample powers [`../preview/map_preview.png`](../preview/),
which is a static PNG rendered via headless Chromium.

[Back to the dataset root](../README.md)
"""

_SPLITS_README_TEMPLATE = """# splits/

**4 files**: pre-filtered per-split parquet files plus the
split manifest.

| file | rows | size |
|------|-----:|-----:|
| `train.parquet` | 11,358,587 | ~10.2 GB |
| `val.parquet`   |  1,419,548 | ~1.3 GB |
| `test.parquet`  |  1,419,328 | ~1.3 GB |
| `split_manifest.json` | — | <100 KB |

Each split file is the entire subset of rows from
[`../combined/all_world.parquet`](../combined/) filtered to one
of `train` / `val` / `test`, with the now-uniform `split`
column dropped. The same 13-column schema (excluding `split`)
applies.

The split is **stratified by country** with a global seed of
**42**. Per-country counts are recorded in
`split_manifest.json`; the totals above match that manifest
exactly. To regenerate with a different seed:

```bash
uv run python scripts/make_split.py --seed 7
uv run python scripts/split_parquets.py
```

For a single-country study it's usually more efficient to load
the per-country parquet from
[`../per_country/<country>/<country>.parquet`](../per_country/)
and filter by `split` in pyarrow, since that file is typically
5-100x smaller than the full combined split.

[Back to the dataset root](../README.md)
"""

_PREVIEW_README_TEMPLATE = """# preview/

**1 file**: `map_preview.png` — a 1600×1100 PNG (~1 MB) showing the
geographic distribution of the full dataset. Same image embedded in
the root README's "Geographic distribution" section.

Generated by `scripts/render_map_screenshot.py`, which renders
[`../sample/sample_map.jsonl`](../sample/sample_map.jsonl) as a folium
map and screenshots it via headless Chromium. The map shows a
**sampled** subset of polygons (~17k representative polygons
across all 284 countries); for the exhaustive 14.2M-polygon list
use [`../combined/all_world.parquet`](../combined/).

[Back to the dataset root](../README.md)
"""

_ROOT_README_INTRO = """# osm-polygon-selection dataset

A curated set of OpenStreetMap polygons from **{n_countries}
geographic units** — *sovereign countries plus sub-country regions*
like Brazilian states, Chinese provinces, Indian zones, US states,
Canadian provinces, Japanese regions, and Indonesian islands —
classified by **size bin** (`small` / `medium` / `large`, area in
[0.1, 100] km²) and tagged by continent (Natural Earth admin0 lookup).

**Size bins:**

- **`small`** — area in **[0.1, 1) km²** (10,000 m² to 1 km², roughly
  100 m × 100 m to ~1 km × 1 km). Examples: a city block, a small
  park, a single farm field, a small wood lot, a residential
  courtyard, a parking lot, an industrial yard.
- **`medium`** — area in **[1, 10) km²** (1 km² to 10 km², roughly
  1 km × 1 km to 3 km × 3 km). Examples: a large park, a small
  village/town footprint, a reservoir, a forest patch, an
  industrial zone, a golf course, a cemetery, a nature reserve.
- **`large`** — area in **[10, 100] km²** (10 km² to 100 km², roughly
  3 km × 3 km to 10 km × 10 km). Examples: a large forest, a
  big lake, an entire town or small city, a large military
  training area, a national park section, a sizable agricultural
  region.

Polygons smaller than 0.1 km² (most individual buildings, houses,
small ponds, single fields) and larger than 100 km² (whole countries,
mountain ranges, big seas) are excluded by the size filter (see
[Filter chain](#filter-chain) below).

**Status:** {status_line}

**Total polygons:** {total_polygons:,}
(combined parquet: `combined/all_world.parquet`).

## Coverage

This dataset processes one parquet per Geofabrik PBF region. Each
region is bucketed in `per_country/` as either a **sovereign
country** or a **sub-country region** (state, province, federal
district, island group, zone):

| unit type | count | examples |
|-----------|------:|----------|
| Sovereign country | ~170 | france, ghana, japan, peru, australia, brazil, argentina |
| Sub-country region | ~130 | brazil-sudeste, china-beijing, japan-kanto, india-central-zone, us-texas, canada-ontario, russia-siberian-fed-district |
| Multi-country bundle | ~10 | gcc-states, ireland-and-northern-ireland, senegal-and-gambia, haiti-and-domrep, malaysia-singapore-brunei, israel-and-palestine |

Total: **{n_countries} geographic units** across all 6 inhabited
continents plus Oceania. The **{n_countries}** is **not** the count
of sovereign states (which is ~195 per the UN); it's the count of
discrete Geofabrik PBF regions we processed.

## Layout

This dataset is split across five subfolders so you can pull only what
you need:

| folder | what's inside | typical size |
|--------|---------------|--------------|
| [`per_country/`](./per_country/) | one folder per country with `<country>.parquet` + `README.md` | ~28 GB total, <1 MB per small country |
| [`combined/`](./combined/) | `all_world.parquet` — every polygon in one file | ~14 GB |
| [`splits/`](./splits/) | `train.parquet`, `val.parquet`, `test.parquet` — pre-filtered split parquets (no `split` column needed) | ~13 GB total |
| [`sample/`](./sample/) | `sample_map.jsonl` — ~18k representative polygons for quick viz | ~3 MB |
| [`preview/`](./preview/) | `map_preview.png` — static map thumbnail | ~1 MB |

Start with `sample/` or `preview/` for a quick look. Pull
`per_country/<country>/<country>.parquet` for a single-country
study. Use `combined/all_world.parquet` for cross-country work
or `splits/<train/val/test>.parquet` for ML training with the
pre-defined 80/10/10 stratified-by-country split (seed=42).

## What's in this dataset

Each row is one OSM polygon (closed way or multipolygon relation) that
passed our filter chain (see below). The polygon **geometry itself**
is included in the row as WKT (or WKB if `OSM_POLYGON_GEOMETRY=wkb`
is set when the dataset is built) so you can render, query, or
reproject it directly without re-deriving from centroid+area.

{schema_table}

## Provenance

- Pipeline version: {pipeline_version}
- Git SHA: {git_sha}
- Built: {built_at}
- Source: Geofabrik regional extracts (`https://download.geofabrik.de/`)
- Whitelist: 22,075 OSM `key=value` tags from osm-stats (see
  `docs/whitelist_decisions.md` in the project repo, or read the
  full rationale in the
  [blog post](https://noeflandre.com/posts/osm-data-analysis)).
  The whitelist is designed to filter polygons by landuse-style
  tags (`natural`, `landuse`, `leisure`, `amenity`, etc.) so the
  dataset focuses on physical land-cover / land-use features
  rather than buildings, addresses, or points of interest.

## Geographic distribution

![polygon distribution across the dataset's countries](./preview/map_preview.png)

(Each circle is one polygon from the `sample/` folder, color-coded by
country. Circle size is proportional to `sqrt(area_km2)`.)

## Size-bin distribution (full dataset)

Counts every polygon in the **{total_polygons:,}-polygon** dataset
by `size_bin`, computed directly from `combined/all_world.parquet`
via `pyarrow.compute.value_counts`. Percentages are exact ratios
over the entire dataset, not a sample.

{size_bin_table}

## Example row

Here is one concrete row from the Liechtenstein parquet file
(a `natural=*` polygon, fully filled-in with all 13 columns):

{example_row_table}

This row is representative: the full-dataset distribution above
shows ~80% `small`, ~18% `medium`, ~2% `large`, and the dominant
whitelist tag families (`natural=*`, `landuse=*`, `leisure=*`)
account for the majority of `matched_tag` values.

## Filter chain

Each polygon in this dataset has passed three filters:

1. **Size filter (Stage 0)**: area in [0.1, 100] km².
   Polygons smaller than 0.1 km² or larger than 100 km² are dropped.
2. **Whitelist filter (Stage 2)**: at least one OSM tag in the
   22,075-tag whitelist. The whitelist is derived from a clustering
   of OSM tags across both `tfidf` and `embeddings` analyses.
3. **Classify (Stage 3)**: continent assigned via Natural Earth
   admin0 shapefile, size_bin assigned by area.

## Train / val / test split

Every row in every parquet (`per_country/<country>/<country>.parquet`
and `combined/all_world.parquet`) carries a **`split`** column with
one of three values: `train`, `val`, or `test`.

| split | ratio | polygons |
|-------|-------|----------|
| train | 80% | {split_train:,} |
| val   | 10% | {split_val:,} |
| test  | 10% | {split_test:,} |
| **Total** | **100%** | **{total_polygons:,}** |

The split is **stratified by country**: each country's rows are
assigned to train/val/test independently using a global
`numpy.random.default_rng` seeded once with **{split_seed}** and
offset per country. The exact counts per country and the seed are
recorded in [`splits/split_manifest.json`](./splits/split_manifest.json).

To load only one split (e.g. for training), filter in pyarrow:
```python
import pyarrow.compute as pc
import pyarrow.parquet as pq
table = pq.read_table("combined/all_world.parquet")
train = table.filter(pc.equal(table["split"], "train"))
```

The split is deterministic and re-runnable:
```bash
uv run python scripts/make_split.py            # default seed=42, 80/10/10
uv run python scripts/make_split.py --seed 7   # different reproducible split
```

## Per-country summary

{country_table}

[Back to the dataset root](./README.md)
"""

# ---------------------------------------------------------------------------
# Constants (the things the templates don't compute)
# ---------------------------------------------------------------------------
# Regional sub-PBFs and curated country notes live in
# osm_polygon_selection.country_notes and are imported above.
# _country_note and _country_source_description are now in the
# country_notes module as country_note and country_source_description.


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _human_size(num_bytes: int) -> str:
    """Render a byte count as a human-readable string."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def _git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True,
            cwd="/Users/noeflandre/osm-polygon-selection",
        ).stdout.strip()
        return out or "unknown"
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# Step functions (pure where possible; do one thing each)
# ---------------------------------------------------------------------------


def write_country_readmes(root: Path, manifest: dict) -> int:
    """Write one README.md per country into per_country/<c>/README.md.

    Returns the number of READMEs written.
    """
    n = 0
    countries = manifest["countries"]
    for c_info in countries:
        c = c_info["country"]
        # Skip countries with no parquet (e.g. killed-mid-pipeline or
        # not yet extracted). Their per_country/<c>/ folder doesn't
        # exist and writing a README there would fail.
        if int(c_info.get("n_polygons", 0)) == 0:
            continue
        out = root / "per_country" / c / "README.md"
        text = _COUNTRY_README_TEMPLATE.format(
            country=c,
            n_polygons=c_info["n_polygons"],
            extract_status=c_info["extract_status"],
            pbf_date=c_info["pbf_date"],
            source_description=country_source_description(c),
            geofabrik_url=geofabrik_url(c),
            note=country_note(c, c_info["n_polygons"], c_info["extract_status"]),
        )
        out.write_text(text)
        n += 1
    return n


def write_folder_readmes(root: Path, manifest: dict) -> int:
    """Write the four folder-level READMEs.

    Returns the number of READMEs written.
    """
    total_polygons = manifest["total_polygons"]
    n_countries = manifest["n_countries"]

    # combined/ — we don't need the actual size; estimate from total rows.
    all_world = root / "combined" / "all_world.parquet"
    if all_world.exists():
        size_human = _human_size(all_world.stat().st_size)
    else:
        size_human = "~9 GB"

    # sample/ — count lines so the README stays accurate.
    sample_path = root / "sample" / "sample_map.jsonl"
    if sample_path.exists():
        n_sample = sum(1 for _ in sample_path.open())
    else:
        n_sample = 4204

    per_country_readme = _PER_COUNTRY_README_TEMPLATE.format(
        n_country_folders=n_countries,
        total_polygons=total_polygons,
        sample_n_polygons=n_sample,
    )
    combined_readme = _COMBINED_README_TEMPLATE.format(
        n_rows=total_polygons,
        n_countries=n_countries,
        size_human=size_human,
    )
    sample_readme = _SAMPLE_README_TEMPLATE.format(n_rows=n_sample)
    preview_readme = _PREVIEW_README_TEMPLATE  # no parameters

    (root / "per_country" / "README.md").write_text(per_country_readme)
    (root / "combined" / "README.md").write_text(combined_readme)
    (root / "sample" / "README.md").write_text(sample_readme)
    (root / "preview" / "README.md").write_text(preview_readme)
    splits_readme = _SPLITS_README_TEMPLATE  # no parameters
    (root / "splits" / "README.md").write_text(splits_readme)
    return 5


def _schema_table_from_manifest(manifest: dict) -> str:
    """Render the column table from manifest.schema (column names only).

    Descriptions are hard-coded (they live in build_dataset.py too);
    we keep them here so this script is self-contained.
    """
    descriptions = {
        "osm_id": "OSM object id (int64).",
        "osm_type": 'OSM object type, "way" or "relation" (string).',
        "centroid_lon": "polygon centroid longitude (WGS84, float64).",
        "centroid_lat": "polygon centroid latitude (WGS84, float64).",
        "area_km2": "polygon area in km² (Web Mercator, float64).",
        "tags": "OSM `key=value` tags (list of strings).",
        "matched_tag": ("the first tag in `tags` that hit the whitelist "
                        "(string, the reason the polygon survived)."),
        "continent": "Natural Earth admin0 lookup of the centroid (string).",
        "size_bin": ('"small" (0.1-1), "medium" (1-10), or "large" '
                     "(10-100) km² (string)."),
        "country": "ISO-style country name (string).",
        "extract_status": ('"clean" (extract ran to completion) or '
                           '"killed" (extract was interrupted) (string).'),
        "pbf_date": "date of the source PBF file (string, from mtime).",
        "geometry_wkt": ("polygon geometry as WKT (WGS84, string). "
                         "Parse with `shapely.wkt.loads(row.geometry_wkt)`."),
        "geometry_wkb": ("polygon geometry as WKB (WGS84, binary). "
                         "Parse with `shapely.wkb.loads(row.geometry_wkb)`."),
        "split": ('"train", "val", or "test" (stratified by country, '
                  'see [Train/val/test split](#train--val--test-split) below).'),
    }
    types = {
        "osm_id": "int64",
        "osm_type": "string",
        "centroid_lon": "float64",
        "centroid_lat": "float64",
        "area_km2": "float64",
        "tags": "list(string)",
        "matched_tag": "string",
        "continent": "string",
        "size_bin": "string",
        "country": "string",
        "extract_status": "string",
        "pbf_date": "string",
        "geometry_wkt": "string",
        "geometry_wkb": "binary",
        "split": "string",
    }
    cols = manifest.get("schema") or list(descriptions.keys())
    rows = ["| column | type | description |", "|--------|------|-------------|"]
    for c in cols:
        rows.append(f"| {c} | {types.get(c, '')} | {descriptions.get(c, '')} |")
    return "\n".join(rows)


def update_root_readme(root: Path) -> None:
    """Rewrite dataset/README.md as the public landing page.

    Uses the manifest's country list and `build_country_table` from
    `osm_polygon_selection.country_table` to render the per-country
    summary. The size-bin and example-row tables come from
    `osm_polygon_selection.sample_table`. No dynamic imports.
    """
    manifest = json.loads((root / "manifest.json").read_text())

    # Status line.
    n_clean = sum(1 for c in manifest["countries"] if c["extract_status"] == "clean")
    n_killed = len(manifest["countries"]) - n_clean
    if n_killed == 0:
        status_line = (
            f"All {n_clean} geographic units are extracted end-to-end."
        )
    else:
        status_line = (
            f"{n_clean} of {len(manifest['countries'])} geographic units "
            f"are clean. {n_killed} unit(s) were killed mid-pipeline "
            f"(see [`per_country/<unit>/README.md`](./per_country/))."
        )

    # Country table — uses the shared build_country_table.
    country_table = build_country_table(manifest["countries"])

    schema_table = _schema_table_from_manifest(manifest)

    # Sample size-bin distribution + example row. Both are pure reads
    # from sample/sample_map.jsonl (or the /tmp fallback).
    sample_path = root / "sample" / "sample_map.jsonl"
    if not sample_path.is_file():
        sample_path = Path("/tmp/sample_map.jsonl")

    # The package's build_example_row_table takes a fallback_dir so
    # the row lookup uses our root instead of the global DATASET_DIR.
    example_row_table = build_example_row_table(sample_path, fallback_dir=root)

    # GLOBAL size-bin distribution: from combined/all_world.parquet so the
    # table reflects every polygon, not a sample.
    from osm_polygon_selection.sample_table import (
        build_size_bin_distribution_table as _build_dist_table,
        compute_global_size_bin_distribution,
    )
    sample_dist = compute_global_size_bin_distribution(root)
    size_bin_table = _build_dist_table(sample_dist)
    sample_n_polygons = sum(n for _, n, _ in sample_dist)

    # Read split manifest if present; default to "no split yet" placeholders
    # so the README renders even before make_split.py has been run.
    split_manifest_path = root / "splits" / "split_manifest.json"
    split_counts: dict[str, int] = {}
    split_seed: int | str = 42
    if split_manifest_path.is_file():
        with split_manifest_path.open() as f:
            sm = json.load(f)
        split_counts = sm.get("counts", {})
        split_seed = sm.get("seed", 42)

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

    text = yaml_frontmatter + _ROOT_README_INTRO.format(
        n_countries=len(manifest["countries"]),
        n_non_europe=sum(
            1 for c in manifest["countries"] if c["country"] in _NON_EUROPE
        ),
        status_line=status_line,
        total_polygons=manifest["total_polygons"],
        schema_table=schema_table,
        pipeline_version=manifest.get("version", "v0.1.0"),
        git_sha=manifest.get("git_sha", _git_sha()),
        built_at=manifest.get("built_at", datetime.now().isoformat()),
        country_table=country_table,
        size_bin_table=size_bin_table,
        split_train=split_counts.get("train", 0),
        split_val=split_counts.get("val", 0),
        split_test=split_counts.get("test", 0),
        split_seed=split_seed,
        example_row_table=example_row_table,
        sample_n_polygons=sample_n_polygons,
    )

    (root / "README.md").write_text(text)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def _sample_src_default() -> Path:
    return Path("/tmp/sample_map.jsonl")


def _preview_src_default() -> Path:
    # The map preview is generated by render_map_screenshot.py at
    # this location (see that script). Return the default; main() will
    # skip the copy if it doesn't exist.
    return Path(
        "/Users/noeflandre/osm-polygon-selection/data/dataset/map_preview.png"
    )


def main(
    root: Path = DEFAULT_ROOT,
    sample_src: Path | None = None,
    preview_src: Path | None = None,
) -> dict:
    """Run the full layout transformation. Returns a summary dict."""
    if not root.is_dir():
        raise SystemExit(f"dataset root does not exist: {root}")
    if not (root / "manifest.json").is_file():
        raise SystemExit(f"missing manifest.json at {root}")

    summary: dict = {"root": str(root), "steps": []}

    # Step 1 — ensure layout.
    ensure_layout(root)
    summary["steps"].append("ensure_layout")

    # Step 2 — load manifest to drive the moves.
    manifest = json.loads((root / "manifest.json").read_text())
    country_names = [c["country"] for c in manifest["countries"]]
    summary["n_countries"] = len(country_names)

    # Step 3 — move per-country parquets.
    n_moved_c = move_country_files(root, country_names)
    summary["countries_moved"] = n_moved_c
    summary["steps"].append("move_country_files")

    # Step 4 — move combined parquet.
    moved_combined = move_combined(root)
    summary["combined_moved"] = moved_combined
    summary["steps"].append("move_combined")

    # Step 5 — copy sample jsonl.
    s_src = sample_src or _sample_src_default()
    copied_sample = move_sample(root, s_src)
    summary["sample_copied"] = copied_sample
    summary["steps"].append("move_sample")

    # Step 6 — copy preview png.
    p_src = preview_src or _preview_src_default()
    copied_preview = move_preview(root, p_src)
    summary["preview_copied"] = copied_preview
    summary["steps"].append("move_preview")

    # Step 7 — country READMEs.
    n_country_readmes = write_country_readmes(root, manifest)
    summary["country_readmes_written"] = n_country_readmes
    summary["steps"].append("write_country_readmes")

    # Step 8 — folder READMEs.
    n_folder_readmes = write_folder_readmes(root, manifest)
    summary["folder_readmes_written"] = n_folder_readmes
    summary["steps"].append("write_folder_readmes")

    # Step 9 — root README.
    update_root_readme(root)
    summary["root_readme_written"] = True
    summary["steps"].append("update_root_readme")

    # Step 10 — clean up any leftover loose files at the root
    # (e.g. an old `map_preview.png` from a previous build_dataset
    # pass that pre-dates this layout script).
    removed = cleanup_loose_root_files(root)
    summary["loose_root_files_removed"] = removed
    summary["steps"].append("cleanup_loose_root_files")

    return summary


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--root", type=Path, default=DEFAULT_ROOT,
        help=f"Dataset root (default: {DEFAULT_ROOT})",
    )
    p.add_argument(
        "--sample-src", type=Path, default=None,
        help="Source sample_map.jsonl (default: /tmp/sample_map.jsonl)",
    )
    p.add_argument(
        "--preview-src", type=Path, default=None,
        help="Source map_preview.png (default: ./data/dataset/map_preview.png)",
    )
    return p.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    s = main(root=args.root, sample_src=args.sample_src, preview_src=args.preview_src)
    print(json.dumps(s, indent=2))

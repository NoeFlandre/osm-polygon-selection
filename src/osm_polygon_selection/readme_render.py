"""README renderers for the public dataset.

Three kinds of README:

1. ``build_root_readme``: the landing-page README at ``dataset/README.md``.
   Includes yaml frontmatter, provenance, schema, sample distribution,
   example row, train/val/test split, per-country table.

2. ``build_folder_readme``: short READMEs in each of the four subfolders
   (``per_country/``, ``combined/``, ``sample/``, ``preview/``).

3. ``build_country_readme``: per-country READMEs in
   ``per_country/<country>/README.md`` with provenance and links.

Plus ``write_metadata_yaml`` for HF's metadata sidecar.

All renderers are pure functions — they take data and return strings.
Writing to disk is the caller's responsibility.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from osm_polygon_selection.country_table import build_country_table
from osm_polygon_selection.git_meta import git_short_sha
from osm_polygon_selection.pbf_meta import geofabrik_url
from osm_polygon_selection.sample_table import (
    build_example_row_table,
    build_size_bin_distribution_table,
    compute_global_size_bin_distribution,
    compute_sample_size_bin_distribution,
)
from osm_polygon_selection.schema_defs import (
    COLUMN_DESCRIPTIONS,
    COLUMN_TYPES,
)
from osm_polygon_selection.country_notes import (
    COUNTRY_NOTES,
)

PIPELINE_VERSION_DEFAULT = "v0.1.0"
# ---------------------------------------------------------------------------
# Root README
# ---------------------------------------------------------------------------

_YAML_FRONTMATTER = """---
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

_ROOT_README_INTRO = """# osm-polygon-selection dataset

A curated set of OpenStreetMap polygons from **{n_countries} countries**,
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

**Total polygons:** {total_polygons:,}
(combined parquet: `combined/all_world.parquet`).

## Layout

This dataset is split across four subfolders so you can pull only what
you need:

| folder | what's inside | typical size |
|--------|---------------|--------------|
| [`per_country/`](./per_country/) | one folder per country with `<country>.parquet` + `README.md` | ~7 GB total, <1 MB per small country |
| [`combined/`](./combined/) | `all_world.parquet` — every polygon in one file | ~9 GB |
| [`sample/`](./sample/) | `sample_map.jsonl` — ~4k representative polygons for quick viz | <1 MB |
| [`preview/`](./preview/) | `map_preview.png` — static map thumbnail | ~1 MB |

Start with `sample/` or `preview/` for a quick look. Pull
`per_country/<country>/<country>.parquet` for a single-country
study. Use `combined/all_world.parquet` for cross-country work.

## Tag selection

A polygon is kept in this dataset if and only if it satisfies two
filters. Both are set intersections on `key=value` strings — there is
no per-key policy and no per-tag count threshold.

1. **Size filter (Stage 0).** The polygon must have area in
   [0.1, 100] km² and be a closed way or multipolygon relation
   (nodes and lines are dropped upstream).
2. **Whitelist filter (Stage 2).** The polygon's `tags` list
   (which is `["key=value", ...]`) must share at least one element
   with the whitelist. This is `set(row["tags"]) & whitelist`,
   evaluated on the first match only.

### How the whitelist was built

The whitelist is the **union of two osm-stats clustering pipelines**
(TF-IDF and embeddings) at both the base-key level and the tag
level. There is no intersection at any stage.

**Layer 1 — base keys kept.** For each pipeline we read its
`base_key_families.xlsx` and take the base keys labeled
`keep = "yes"`. The whitelist keeps the union of the two
`yes` sets — a base key survives if either pipeline labels it
`yes`.

| Pipeline    | base keys | yes | uncertain | no |
|-------------|----------:|----:|----------:|---:|
| TF-IDF      |       427 | 157 |        54 | 216 |
| Embeddings  |       433 | 169 |        57 | 207 |
| **Union**   |     —     |**236** | — | — |

Of the 236 union base keys, 90 are labeled `yes` in both
pipelines, 67 are TF-IDF-only, and 79 are embeddings-only.

**Layer 2 — tags from each pipeline.** For each kept base key
we expand to specific `key=value` strings from the
corresponding `cluster_memberships*.csv`. Two tiers:

- **Tier A** — every tag from a non-noise HDBSCAN cluster
  (`cluster_id != -1`), always included.
- **Tier B** — HDBSCAN noise points (`cluster_id == -1`) are
  included only when `count_all >= 10,000`. These are
  high-volume isolated tags that escaped clustering (e.g.
  `landuse=forest` at ~5.9 M occurrences, `natural=wood` at
  ~12.4 M occurrences).

Each pipeline then produces its own tag set:

| Pipeline    | tags |
|-------------|-----:|
| TF-IDF      | 17,856 |
| Embeddings  | 19,405 |
| **Intersection** | 15,186 |
| **Union (final whitelist)** | **22,075** |

The final whitelist is the **union of the two pipelines' tag
sets** (TF-IDF ∪ embeddings), deduplicated via Python `set`. Of
the 22,075 unique `key=value` strings, 15,186 appear in both
pipelines, 2,670 are TF-IDF-only, and 4,219 are embeddings-only.
The whitelist is loaded by Stage 2 as a Python `set[str]` for
O(1) intersection.

The full pipeline is documented in
[`docs/whitelist_decisions.md`](https://github.com/NoeFlandre/osm-polygon-selection/blob/main/docs/whitelist_decisions.md)
and the clustering methodology in the accompanying
[blog post](https://noeflandre.com/posts/osm-data-analysis).

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
- OSM tag whitelist: **22,075 unique `key=value` tags**, the
  deduplicated union of two complementary clustering pipelines
  derived from the [osm-stats](https://github.com/NoeFlandre/osm-stats)
  analysis of the OpenStreetMap global tag corpus. The full
  methodology is described in the accompanying blog post,
  [OSM data analysis for landuse](https://noeflandre.com/posts/osm-data-analysis).

  Both pipelines start from the same input — every `(key, value)`
  pair in OSM standardized to lowercase, joined as `key|value`,
  and filtered to tags with `count_all >= 500`, yielding **225,684
  unique tags** representing **3.37 B total occurrences** — and
  produce independent clusterings of this corpus:

  - **TF-IDF (character n-grams) pipeline.** Each tag is tokenized
    into character n-grams of length 3-5. The corpus is represented
    as a sparse TF-IDF matrix (224,123 rows × 396,969 n-grams;
    density 0.014 %), reduced with Truncated SVD to 50 dimensions,
    then clustered with HDBSCAN (`min_cluster_size=5`,
    `min_samples=2`, Euclidean distance). This yields **8,833
    clusters** plus **78,270 noise points** (34.7 % noise ratio).
    TF-IDF catches canonical high-volume forms
    (`landuse=residential`, `natural=water`) and is robust to
    small spelling variants that still share n-grams.

  - **Embeddings (potion-base-8M) pipeline.** Each tag is embedded
    with [`potion-base-8M`](https://github.com/MinishLab/model2vec),
    a 32 M-parameter static-vector table distilled from
    `BGE-base-en-v1.5`. The embeddings are L2-normalized, reduced
    with Truncated SVD to 50 dimensions, then clustered with
    HDBSCAN over Euclidean distance. This yields **4,955 clusters**
    plus **106,498 noise points** (47.2 % noise ratio). The
    semantic embeddings catch synonyms that share no surface
    tokens — `landuse=farmyard` lands near `landuse=meadow` near
    `landuse=farmland` — which TF-IDF would scatter.

  After clustering, each pipeline produces a per-base-key label
  (`keep = yes | uncertain | no`) covering 427 base keys (TF-IDF:
  157 yes / 54 uncertain / 216 no) and 433 base keys (embeddings:
  169 yes / 57 uncertain / 207 no). The whitelist takes the union
  of the two `yes` sets, yielding **236 base keys**.

  For each kept base key, the whitelist extracts two tiers of
  `key=value` tags from the corresponding cluster memberships:

  - **Tier A (real clusters):** every tag from a non-noise
    HDBSCAN cluster (`cluster_id != -1`) — 16,685 tags from
    TF-IDF and 18,382 from embeddings (pre-dedup).
  - **Tier B (noise rescue):** HDBSCAN noise points
    (`cluster_id == -1`) with `count_all >= 10,000` — high-volume
    isolated tags that escaped clustering (e.g. `landuse=forest`
    at ~5.9 M occurrences, `natural=wood` at ~12.4 M occurrences).
    1,171 tags from TF-IDF and 1,023 from embeddings.

  After Python `set` deduplication across both pipelines, the
  final whitelist contains **22,075 unique `key=value` strings**
  and is loaded by Stage 2 as a Python `set[str]` for O(1)
  intersection.

## Geographic distribution

![polygon distribution across the dataset's countries](./preview/map_preview.png)

A spatial sample of ~4 k representative polygons (one per grid
cell per country, power-law capped at 200 per country) rendered
on a folium basemap. See [`sample/`](./sample/) for the source
JSONL.

## Size-bin distribution (full dataset)

Counts every polygon in the {total_polygons:,}-polygon dataset by
`size_bin`, computed directly from `combined/all_world.parquet`
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

1. **Size filter (Stage 0)**: area in [0.1, 100] km². Polygons
   smaller than 0.1 km² or larger than 100 km² are dropped before
   any tag-based filtering.
2. **Whitelist filter (Stage 2)**: at least one OSM tag in the
   22,075-tag whitelist described above. Stage 2 keeps only
   polygons whose `tags` list intersects the whitelist set,
   recording the first match as `matched_tag`.
3. **Classify (Stage 3)**: continent assigned via Natural Earth
   admin0 shapefile (centroid point-in-polygon), `size_bin`
   assigned by area.

Per-country retention after whitelist filtering ranges from
~93 % (large countries with significant urban address-tag
coverage) to ~99.9 % (sparser regions where almost every
polygon carries a `natural=*` or `landuse=*` tag).

{split_section}

## Per-country summary

{country_table}

[Back to the dataset root](./README.md)
"""


_SPLIT_SECTION_TEMPLATE = """## Train / val / test split

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
"""


def _split_section(root: Path) -> str:
    """Return the split section markdown, or '' if no split manifest."""
    split_manifest_path = root / "splits" / "split_manifest.json"
    if not split_manifest_path.is_file():
        return ""
    with split_manifest_path.open() as f:
        sm = json.load(f)
    counts = sm.get("counts", {})
    return _SPLIT_SECTION_TEMPLATE.format(
        split_train=counts.get("train", 0),
        split_val=counts.get("val", 0),
        split_test=counts.get("test", 0),
        total_polygons=sm.get("n_countries", 0),  # placeholder; overridden below
        split_seed=sm.get("seed", 42),
    )


def _schema_table_from_manifest(manifest: dict) -> str:
    """Build the schema markdown table from the manifest's schema list."""
    cols = manifest.get("schema") or list(COLUMN_DESCRIPTIONS.keys())
    lines = ["| column | type | description |", "|--------|------|-------------|"]
    for c in cols:
        lines.append(f"| {c} | {COLUMN_TYPES.get(c, '')} | {COLUMN_DESCRIPTIONS.get(c, '')} |")
    return "\n".join(lines)


def build_root_readme(manifest: dict, root: Path) -> str:
    """Render the full root README.md content.

    Args:
        manifest: the parsed manifest.json dict (must include
            ``countries``, ``total_polygons``, ``n_countries``,
            ``version``, ``git_sha``, ``built_at``, ``schema``).
        root: dataset root directory (used to locate the sample JSONL
            and splits manifest).

    Returns the full README text (including yaml frontmatter).
    """
    countries = manifest.get("countries", [])
    n_countries = len(countries)
    total_polygons = manifest.get("total_polygons", 0)

    # Imported lazily to avoid a circular import with paths.py.
    from osm_polygon_selection.pbf_meta import NON_EUROPE_COUNTRIES
    n_non_europe = sum(1 for c in countries if c["country"] in NON_EUROPE_COUNTRIES)

    sample_path = root / "sample" / "sample_map.jsonl"
    if not sample_path.is_file():
        sample_path = Path("/tmp/sample_map.jsonl")
    # GLOBAL size-bin distribution (full dataset, not sample).
    dist = compute_global_size_bin_distribution(root)
    size_bin_table = build_size_bin_distribution_table(dist)
    sample_n_polygons = sum(n for _, n, _ in dist)

    schema_table = _schema_table_from_manifest(manifest)
    country_table = build_country_table(countries)
    split_section = _split_section(root)

    # If split section is present, replace its placeholder for total
    # with the actual dataset total.
    if split_section:
        split_counts_path = root / "splits" / "split_manifest.json"
        if split_counts_path.is_file():
            with split_counts_path.open() as f:
                sm = json.load(f)
            split_total = sm.get("n_countries_total", total_polygons)
            split_section = split_section.replace(
                f"**{sm.get('n_countries', 0):,}**",
                f"**{split_total:,}**",
            )

    text = _YAML_FRONTMATTER + _ROOT_README_INTRO.format(
        n_countries=n_countries,
        n_non_europe=n_non_europe,
        total_polygons=total_polygons,
        schema_table=schema_table,
        pipeline_version=manifest.get("version", PIPELINE_VERSION_DEFAULT),
        git_sha=manifest.get("git_sha", git_short_sha()),
        built_at=manifest.get("built_at", datetime.now().isoformat()),
        country_table=country_table,
        size_bin_table=size_bin_table,
        example_row_table=build_example_row_table(sample_path, fallback_dir=root),
        sample_n_polygons=sample_n_polygons,
        split_section=split_section,
    )
    return text


# ---------------------------------------------------------------------------
# Folder READMEs
# ---------------------------------------------------------------------------

_FOLDER_TEMPLATES: dict[str, str] = {
    "per_country": """# per_country/

{n_countries} country folders (one folder per country). Each contains:

- `<country>.parquet` — all polygons for that country (schema matches the root README).
- `README.md` — country-specific notes (pbf date, source sub-PBFs if any, polygon count).

Pull a single country with:
```python
import pyarrow.parquet as pq
t = pq.read_table("per_country/france/france.parquet")
```
""",
    "combined": """# combined/

Single parquet containing every polygon across all {n_countries} countries.

- `all_world.parquet` — schema matches the root README. Includes a `split` column (`train`/`val`/`test`) if `make_split.py` has been run.

Use this for cross-country work. For per-country analysis, pull from `per_country/` instead (smaller per-file download).
""",
    "sample": """# sample/

A geographically-stratified sample of polygons for quick visualization and ad-hoc queries.

- `sample_map.jsonl` — one JSON object per polygon, ~4k polygons across all {n_countries} countries. The same file that backs `preview/map_preview.png`.
""",
    "preview": """# preview/

Static thumbnail of the dataset's geographic distribution.

- `map_preview.png` — 1600×1100 PNG, circles colored by country. **Sample only** (not exhaustive) — see [`sample/`](../sample/) for how the sample is built.
""",
}


def build_folder_readme(folder: str, n_countries: int) -> str:
    """Render a short README for one of the four subfolders."""
    if folder not in _FOLDER_TEMPLATES:
        raise ValueError(f"unknown folder: {folder!r}; expected one of {list(_FOLDER_TEMPLATES)}")
    return _FOLDER_TEMPLATES[folder].format(n_countries=n_countries)


# ---------------------------------------------------------------------------
# Country README
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
| source | `{country}-latest.osm.pbf` |
| Geofabrik extract | <{geofabrik_url}> |

## Geometry

The parquet file in this folder (`{country}.parquet`) has the same schema as
the combined `combined/all_world.parquet`. Each row carries the polygon
**geometry as WKT** (default), plus centroid + area + the whitelist-matched tag.

Load with:
```python
import pyarrow.parquet as pq
table = pq.read_table("per_country/{country}/{country}.parquet")
df = table.to_pandas()
```

## Notes

{country_note}
"""


def _country_note(country: str, n_polygons: int) -> str:
    """Return a 1-2 sentence note about this country, or generic fallback.

    Sources curated notes from ``osm_polygon_selection.country_notes``;
    falls back to a generic line sized to the polygon count.
    """
    note = COUNTRY_NOTES.get(country, "")
    if note:
        return note
    if n_polygons <= 100:
        return f"Tiny country with only {n_polygons:,} polygons surviving the size filter."
    if n_polygons <= 5000:
        return f"Small country with {n_polygons:,} polygons. Most urban + coastal features."
    return ""


def build_country_readme(
    country: str,
    n_polygons: int,
    extract_status: str,
    pbf_date: str,
) -> str:
    """Render the per-country README content."""
    note = _country_note(country, n_polygons) or "Standard coverage."
    return _COUNTRY_README_TEMPLATE.format(
        country=country,
        n_polygons=n_polygons,
        extract_status=extract_status,
        pbf_date=pbf_date,
        geofabrik_url=geofabrik_url(country),
        country_note=note,
    )


# ---------------------------------------------------------------------------
# Metadata YAML (HF sidecar)
# ---------------------------------------------------------------------------

_METADATA_YAML = """license: odbl
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


def write_metadata_yaml(out_dir: Path) -> None:
    """Write HF's required metadata sidecar at ``out_dir/metadata.yaml``."""
    (out_dir / "metadata.yaml").write_text(_METADATA_YAML)


# Re-exported for convenience.
__all__ = [
    "PIPELINE_VERSION_DEFAULT",
    "build_root_readme",
    "build_folder_readme",
    "build_country_readme",
    "write_metadata_yaml",
]

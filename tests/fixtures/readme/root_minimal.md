---
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
# osm-polygon-selection dataset

A curated set of OpenStreetMap polygons from **2 countries**,
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

**Total polygons:** 150,000
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

| column | type | description |
|--------|------|-------------|
| osm_id | int64 | OSM object id (int64). |
| osm_type | string | OSM object type, "way" or "relation" (string). |
| centroid_lon | float64 | polygon centroid longitude (WGS84, float64). |
| centroid_lat | float64 | polygon centroid latitude (WGS84, float64). |
| area_km2 | float64 | polygon area in km² (Web Mercator, float64). |
| tags | list(string) | OSM `key=value` tags (list of strings). |
| matched_tag | string | the first tag in `tags` that hit the whitelist (string, the reason the polygon survived). |
| continent | string | Natural Earth admin0 lookup of the centroid (string). |
| size_bin | string | "small" (0.1-1), "medium" (1-10), or "large" (10-100) km² (string). |
| country | string | ISO-style country name (string). |
| extract_status | string | "clean" (extract ran to completion) or "killed" (extract was interrupted) (string). |
| pbf_date | string | date of the source PBF file (string, from mtime). |
| geometry_wkt | string | polygon geometry as WKT (WGS84, string). Parse with `shapely.wkt.loads(row.geometry_wkt)`. |

## Provenance

- Pipeline version: v0.1.0
- Git SHA: abc1234
- Built: 2026-01-01T00:00:00
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

Counts every polygon in the 150,000-polygon dataset by
`size_bin`, computed directly from `combined/all_world.parquet`
via `pyarrow.compute.value_counts`. Percentages are exact ratios
over the entire dataset, not a sample.

| size_bin | count | pct |
|----------|-------|-----|
| small | 0 | 0.0% |
| medium | 0 | 0.0% |
| large | 0 | 0.0% |
| **Total** | 0 | 100.0% |


## Example row

Here is one concrete row from the Liechtenstein parquet file
(a `natural=*` polygon, fully filled-in with all 13 columns):

| column | value |
|--------|-------|
| osm_id | `2247244492` |
| osm_type | *(none)* |
| centroid_lon | 9.525487 |
| centroid_lat | 47.058574 |
| area_km2 | 0.1048 |
| tags | *(none)* |
| matched_tag | `natural=bare_rock` |
| continent | `Europe` |
| size_bin | `small` |
| country | `liechtenstein` |
| extract_status | *(none)* |
| pbf_date | *(none)* |
| geometry_wkt | *(none)* |


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



## Per-country summary

| Country | Polygons | Status |
|---------|----------|--------|
| france | 100,000 | clean |
| germany | 50,000 | clean |
| **Total** | 150,000 | |

[Back to the dataset root](./README.md)

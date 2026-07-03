# osm-polygon-selection

A curated set of OpenStreetMap (OSM) polygons, classified by
**continent** (Natural Earth admin0 lookup) and **size bin**
(`small` / `medium` / `large`, area in `[0.1, 100]` km²), stratified
by country, and published on Hugging Face.

Built with TDD (red-green-modular), optimized end-to-end, and
actively expanding — currently covers **78 countries** (49 European
+ 29 African), **7,490,239 polygons** across `combined/all_europe.parquet`
(zstd, ~6.0 GB) and 77 per-country parquets.

---

## Quickstart (TL;DR for a fresh session)

```bash
# 1. Set the HDD env vars (CRITICAL — see docs/AGENT_HANDOFF.md)
export OSM_DATA_ROOT="/Volumes/Seagate M3/osm-polygon-selection"
export OSM_DATASET_DIR="/Volumes/Seagate M3/osm-polygon-selection/dataset"

# 2. Verify state (everything is on the HDD, not the repo)
ls $OSM_DATA_ROOT/{raw,processed,dataset}
ls $OSM_DATASET_DIR/{combined,per_country,splits,sample,preview}

# 3. Run the test suite — must be ≥ 278 passing
uv run pytest tests/ --deselect tests/stages/test_extract_perf.py::TestWallClockCap::test_wall_clock_cap_stops_clean

# 4. Add a new country end-to-end:
cd /Users/noeflandre/osm-polygon-selection
COUNTRY=mayotte        # smallest unprocessed African
mkdir -p $OSM_DATA_ROOT/processed/$COUNTRY
curl -L -o $OSM_DATA_ROOT/raw/$COUNTRY-latest.osm.pbf \
  https://download.geofabrik.de/africa/$COUNTRY-latest.osm.pbf

OSM_DATA_ROOT=$OSM_DATA_ROOT uv run scripts/stage0_extract.py \
  $OSM_DATA_ROOT/raw/$COUNTRY-latest.osm.pbf \
  $OSM_DATA_ROOT/processed/$COUNTRY/01_extracted.jsonl
OSM_DATA_ROOT=$OSM_DATA_ROOT uv run scripts/stage2_filter.py \
  $OSM_DATA_ROOT/processed/$COUNTRY/01_extracted.jsonl \
  $OSM_DATA_ROOT/whitelist.json \
  $OSM_DATA_ROOT/processed/$COUNTRY/02_filtered.jsonl
OSM_DATA_ROOT=$OSM_DATA_ROOT uv run scripts/stage3_classify.py \
  $OSM_DATA_ROOT/processed/$COUNTRY/02_filtered.jsonl \
  data/reference/natural_earth/ne_110m_admin_0_countries.shp \
  $OSM_DATA_ROOT/processed/$COUNTRY/03_classified.jsonl

# Then build + organize + sample + split + render + HF upload
OSM_DATA_ROOT=$OSM_DATA_ROOT OSM_DATASET_DIR=$OSM_DATASET_DIR \
  uv run scripts/build_dataset.py
OSM_DATASET_DIR=$OSM_DATASET_DIR uv run scripts/organize_dataset.py \
  --root $OSM_DATASET_DIR
OSM_DATASET_DIR=$OSM_DATASET_DIR uv run scripts/sample_for_map.py
OSM_DATASET_DIR=$OSM_DATASET_DIR uv run scripts/make_split.py
uv run scripts/visualize.py $OSM_DATASET_DIR/sample/sample_map.jsonl /tmp/map.html
uv run scripts/render_map_screenshot.py
cp data/dataset/map_preview.png $OSM_DATASET_DIR/preview/map_preview.png
uv run scripts/upload_to_hf.py
```

**Always** read `docs/AGENT_HANDOFF.md` before doing anything. It
captures all the conventions, gotchas, TDD workflow, and storage
policy that took months to learn.

---

## What's in the dataset

| Region              | Countries | Polygons |
|---------------------|----------:|---------:|
| Europe              |        49 | 7,302,782 |
| North Africa        |         4 |   96,768 |
| Sub-Saharan Africa  |        25 |   90,689 |
| **Total**           |    **78** | **7,490,239** |

(The continent breakdown is approximate; the per-country numbers are
exact. See `dataset/manifest.json` for the machine-readable source.)

Each row in `combined/all_europe.parquet` is one OSM polygon (closed
way or multipolygon relation) that:

1. Survived the size filter (`0.1 ≤ area_km2 ≤ 100`).
2. Has at least one OSM `key=value` tag that hit the
   [22,075-tag whitelist](https://github.com/NoeFlandre/osm-stats).
3. Was classified by continent (Natural Earth admin0 lookup of the
   centroid) and size bin (area in km²).

### Tag whitelist: how polygons are filtered against OSM tags

The whitelist selects polygons whose tags describe physical
land-use / land-cover (e.g. `natural=wood`, `landuse=forest`,
`leisure=park`) rather than abstract entities (buildings,
addresses, points of interest). It is the **union of two
complementary osm-stats pipelines**, run on the same OSM tag
corpus and then merged.

#### Step 1 — Tag corpus

osm-stats first extracts every `(key, value)` tuple from OSM,
counts occurrences (`count_all`), and groups rows by
`base_key` (the part before any `:` in the key — e.g.
`landuse`, `natural`, `leisure`, `amenity`, `highway`,
`building`, `addr:housenumber`, …). The two pipelines then
cluster this corpus independently.

#### Step 2 — TF-IDF pipeline (lexical similarity)

`data/reference/osm_stats/tfidf/cluster_memberships.csv`
(225,684 rows; 1,829 base keys; 8,833 HDBSCAN clusters).

- **Vectorization:** each `key=value` tag is tokenized into
  word pieces (`landuse`, `forest`, `natural`, `wood`, …) and
  represented as a sparse TF-IDF vector over the full corpus
  vocabulary. Stop-words and pure numbers are filtered out.
- **Clustering:** HDBSCAN over the TF-IDF cosine-distance
  matrix. Yields ~150 superclusters per active base key.
- **Strength:** captures canonical high-volume forms that look
  lexically identical — `landuse=residential`, `natural=water`,
  `highway=residential`. Robust to spelling variants when the
  shared token is dominant.
- **Weakness:** cannot connect tags that share no surface
  tokens — `landuse=farmyard`, `landuse=meadow`,
  `landuse=farmland` end up in different clusters because the
  rare tokens don't overlap.

#### Step 3 — Embeddings pipeline (semantic similarity)

`data/reference/osm_stats/embeddings/cluster_memberships_embeddings.csv`
(225,684 rows; 1,829 base keys; 4,955 HDBSCAN clusters).

- **Vectorization:** each `key=value` tag is embedded with a
  sentence-transformer model (`all-MiniLM-L6-v2` by default in
  osm-stats) and L2-normalized to a dense 384-dim vector.
- **Clustering:** HDBSCAN over the cosine-distance matrix of
  the embedding vectors. Produces fewer, broader clusters
  (~150 superclusters per active base key, but with much
  wider semantic coverage).
- **Strength:** catches semantic synonyms — `landuse=farmyard`
  ≈ `landuse=meadow` ≈ `landuse=farmland` end up in the same
  supercluster because their embeddings sit close together
  in vector space even though their tokens don't overlap.
- **Weakness:** smaller, rarer tags get pulled toward whatever
  cluster centroid is nearest, which can produce false-positive
  groupings (e.g. `natural=bare_rock` near `natural=cliff`).
  Filtered downstream by the manual labels.

#### Step 4 — Manual labeling per base key

For each base key, a human labeler examined the
superclusters produced by each pipeline and assigned a
`keep=yes | uncertain | no` label:

| Pipeline  | base keys | yes  | uncertain | no  |
|-----------|----------:|-----:|----------:|----:|
| TF-IDF    |       427 |  157 |        54 | 216 |
| Embeddings|       433 |  169 |        57 | 207 |

A base key is kept if **either** pipeline labels it `yes` (90
overlap; 67 TF-IDF-only; 79 embeddings-only). The union yields
**236 base keys** that feed the dataset.

#### Step 5 — Two-tier tag extraction per kept base key

For each `(base_key, key, value)` row in the cluster_memberships
files, we include it in the final whitelist if:

- **Tier A (real clusters):** `cluster_id != -1`. Always
  included. Yields **16,685 tags from TF-IDF + 18,382 from
  embeddings** (pre-dedup).
- **Tier B (noise rescue):** `cluster_id == -1` (HDBSCAN noise)
  **and** `count_all >= 10,000`. These are high-volume tags
  that HDBSCAN failed to cluster because they have no near
  duplicate — typically canonical isolated tags like
  `landuse=forest` (~5.9 M occurrences) or `natural=wood`
  (~12.4 M occurrences). Yields **1,171 tags from TF-IDF +
  1,023 from embeddings**.

After Python `set` dedup across both pipelines, the final
whitelist contains **22,075 unique `key=value` strings** and
is written to `data/whitelist.json` as a sorted JSON array
(loaded downstream as a Python `set[str]` for O(1)
intersection).

#### Step 6 — Filtering at Stage 2

For each polygon in `01_extracted.jsonl` (Stage 0 output),
Stage 2 walks its `tags` list and keeps the polygon iff at
least one tag intersects the whitelist set. The first
whitelist hit is recorded as `matched_tag` (the other
schema column `tags` keeps the full original list as a
`pa.list_(pa.string())` for downstream re-filtering). A
typical run keeps **~99 %** of input polygons (the rest are
tagged with administrative / address / unclassified keys
only).

Per-country retention in the current dataset ranges from
**~93 %** (kenya, large address-heavy urban coverage) to
**~99.9 %** (lesotho, where almost every polygon has at
least one `natural=*` or `landuse=*` tag).

#### What we explicitly do NOT do

- **No re-clustering** — osm-stats HDBSCAN output is taken
  as-is.
- **No `count_all` threshold on Tier A** — would drop
  legitimate per-value tags.
- **No `sc_is_polygon_friendly` filter** — Stage 0 already
  drops non-polygon geometries upstream.
- **No whitening of values across pipelines** — duplicates
  are removed via `set` dedup, but conflicting keep labels
  across pipelines (e.g. base key `yes` in one, `no` in the
  other) take the **union**: `yes` wins.

See `docs/whitelist_decisions.md` for the rationale and
edge-case decisions, and
`docs/ARCHITECTURE.md` for the data flow.

---

## Pipeline (staged, resumable)

```
Stage 0  scripts/stage0_extract.py        PBF          -> 01_extracted.jsonl
Stage 1  scripts/stage1_build_whitelist.py osm-stats    -> whitelist.json
Stage 2  scripts/stage2_filter.py         JSONL + WL   -> 02_filtered.jsonl
Stage 3  scripts/stage3_classify.py       JSONL + shp  -> 03_classified.jsonl
                                                 (continent + size_bin)
```

Then dataset assembly:

```
build_dataset.py     03_classified.jsonl per country -> per_country/<c>/<c>.parquet
                                                  -> combined/all_europe.parquet
organize_dataset.py  flat dataset/  ->  per_country/, combined/, sample/, preview/
sample_for_map.py    combined       ->  sample/sample_map.jsonl (5000 stratified)
make_split.py        combined       ->  combined/all_europe.parquet (with split col)
                                       + splits/split_manifest.json
upload_to_hf.py      dataset/       ->  HuggingFace dataset (NoeFlandre/...)
```

Stages 0-3 are **resumable**: a write-ahead log (`*.seen_ids`) tracks
already-processed OSM IDs so re-running picks up exactly where it
left off after a crash or interrupt. See `scripts/stage0_extract.py`
for `--limit` and `--max-seconds` caps.

The build/split/upload steps are **idempotent**: re-running them
with the same inputs produces identical outputs (modulo timestamps).

---

## Repository layout

```
src/osm_polygon_selection/      library modules (importable)
  core/                         pipeline-agnostic primitives
    geometry_utils.py             CRS / area / centroid
    jsonl_utils.py                JSONL streaming helpers
    streaming_writer.py           pa.json zstd streaming parquet writer
    whitelist_io.py               whitelist.json read/write
  stages/                       one module per pipeline stage
    extract.py                    Stage 0: PBF streaming (osmium)
    whitelist.py                  Stage 1: OSM tag whitelist from osm-stats
    filter_by_whitelist.py        Stage 2: tag-intersection filter
    classify.py                   Stage 3: continent + size_bin
  paths.py                      OSM_DATA_ROOT + OSM_DATASET_DIR env var resolution
  pbf_meta.py                   NON_EUROPE_COUNTRIES + geofabrik_url()
  schema_defs.py                pyarrow schema + column descriptions
  readme_render.py              root + per-country + folder README rendering
  country_table.py              markdown table of countries
  sample_table.py               sample/size-bin distribution table
  dataset_layout.py             moves flat dataset/ -> per_country/ + combined/
                                + sample/ + preview/
  git_meta.py                   git_short_sha() for HF repo card
  extract_status.py             "clean" vs "killed" classifier

scripts/                        CLI entry points (one per stage)
  stage0_extract.py             Stage 0 (with --max-seconds + --limit caps)
  stage1_build_whitelist.py     Stage 1 (one-time per machine)
  stage2_filter.py              Stage 2
  stage3_classify.py            Stage 3
  build_dataset.py              Stage 0-3 outputs -> parquet dataset
  organize_dataset.py           flat dataset/ -> HF viewer layout
  sample_for_map.py             combined -> 5000-row stratified sample
  make_split.py                 train/val/test split (seed=42)
  upload_to_hf.py               push to HuggingFace
  visualize.py                  JSONL -> interactive HTML map (folium)
  render_map_screenshot.py      HTML -> static map_preview.png
  run_country.sh                one-country shortcut
  run_europe.py                 legacy loop driver

tests/                          pytest suite (280 tests, 278 passing)
  core/                         primitive tests
  stages/                       per-stage tests
  test_*.py                     per-script integration tests
                                (build_dataset, make_split, sample_for_map,
                                 organize_dataset, upload_to_hf, pbf_meta,
                                 readme_render, ...)

data/                           LOCAL-ONLY (gitignored, NOT the source of truth)
  reference/                    static reference data
    natural_earth/                admin0 shapefile (public domain)
    osm_stats/                    tag analysis CSVs + XLSX (MIT)
  whitelist.json                global whitelist (built by stage 1)
                                (kept locally so stage 2 doesn't need osm-stats)

docs/                           markdown knowledge base
  AGENT_HANDOFF.md              conventions, gotchas, TDD workflow — READ FIRST
  ARCHITECTURE.md               deep dive on each module + data flow
  PERFORMANCE.md                benchmarks + optimizations applied
  AFRICA_ROLLOUT.md             /africa/ loop state, queue, partial dirs
  dataset_state.md              live state doc (rebuilt every commit)
  whitelist_decisions.md        rationale for whitelist filtering

.claude.md                      local agent memory (gitignored — DO NOT COMMIT
                                hard rules; this is the storage policy + TDD
                                loop conventions that would otherwise be lost
                                between sessions)
```

---

## Storage policy (READ THIS)

**The dataset lives on the external HDD, never the MacBook SSD.**

- HDD root: `/Volumes/Seagate M3/osm-polygon-selection/`
  - `raw/`: downloaded Geofabrik PBFs (~6 GB for batch 3 PBFs alone).
  - `processed/<country>/`: per-country stage 0/2/3 outputs.
  - `dataset/`: final per-country parquets, combined parquet,
    splits, sample, READMEs, manifest, metadata.
- MacBook local `data/`, `processed/`, `raw/` MUST stay empty.
- The pipeline scripts honor two env vars: `OSM_DATA_ROOT` and
  `OSM_DATASET_DIR`. Without them, scripts fall back to a sibling
  path off the project root (e.g. `~/osm-polygon-selection-dataset/`)
  which silently fills up the SSD. **Always** export both.

See `docs/AGENT_HANDOFF.md` for the full storage policy.

---

## Tests

```bash
# Must stay ≥ 278 passing before any commit
uv run pytest tests/ \
  --deselect tests/stages/test_extract_perf.py::TestWallClockCap::test_wall_clock_cap_stops_clean
```

The deselect is for a pre-existing flaky test (SIGALRM at teardown)
that has nothing to do with our pipeline.

TDD workflow is mandatory for any new feature or bugfix. See
`docs/AGENT_HANDOFF.md` for the red-green-modular loop.

---

## Data attribution

- OSM data: (c) OpenStreetMap contributors, ODbL 1.0
- Natural Earth: public domain, naturalearthdata.com
- osm-stats analysis: github.com/NoeFlandre/osm-stats (MIT code)

## Hugging Face bucket

Final dataset published at:

- **Repo:** `NoeFlandre/osm-polygon-selection` (dataset type)
- **Layout:** `per_country/<country>/{README.md, <country>.parquet}`,
  `combined/{README.md, all_europe.parquet}`, `sample/`, `preview/`,
  root `README.md`, `manifest.json`, `metadata.yaml`.
- **Compression:** zstd level 1 (~36% smaller than snappy).
- **Row group size:** 50k rows (~50-60 MB per group, well under
  HF viewer's 300 MB scan limit).

Heavy source data (PBFs, shapefiles, osm-stats references) is stored
on the HDD only — not on Hugging Face.

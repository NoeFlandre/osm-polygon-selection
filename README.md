# osm-polygon-selection

A curated set of OpenStreetMap (OSM) polygons, classified by
**continent** (Natural Earth admin0 lookup) and **size bin**
(`small` / `medium` / `large`, area in `[0.1, 100]` km²), stratified
by country, and published on Hugging Face.

Built with TDD (red-green-modular), optimized end-to-end, and
actively expanding — currently covers **77 countries** (49 European
+ 28 African), **7,484,912 polygons** across `combined/all_europe.parquet`
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
| Europe              |        49 | 7,385,553 |
| North Africa        |         5 |  151,083 |
| Sub-Saharan Africa  |        23 |  116,276 |
| **Total**           |    **77** | **7,484,912** |

(The continent breakdown is approximate; the per-country numbers are
exact. See `dataset/manifest.json` for the machine-readable source.)

Each row in `combined/all_europe.parquet` is one OSM polygon (closed
way or multipolygon relation) that:

1. Survived the size filter (`0.1 ≤ area_km2 ≤ 100`).
2. Has at least one OSM `key=value` tag that hit the
   [22,075-tag whitelist](https://github.com/NoeFlandre/osm-stats).
3. Was classified by continent (Natural Earth admin0 lookup of the
   centroid) and size bin (area in km²).

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

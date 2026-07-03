# Architecture

This document explains how the OSM polygon pipeline works end-to-end.
For conventions + storage policy + TDD workflow, see
`docs/AGENT_HANDOFF.md`.

---

## 1. Data flow (the 7 layers)

```
                                  HDD only                          local repo
                                ┌──────────────────────────┐    ┌──────────────────┐
                                │ raw/                     │    │ data/reference/  │
                                │  <country>-latest.osm.pbf│    │  natural_earth/  │
                                │                          │    │  osm_stats/      │
                                │ processed/<country>/     │    └──────────────────┘
                                │  01_extracted.jsonl      │
                                │   .seen_ids   (WAL)      │
                                │   .run.json   (metrics)  │
                                │   .progress.json        │
                                │  02_filtered.jsonl       │
                                │  03_classified.jsonl     │
                                │                          │
                                │ dataset/                 │
                                │  per_country/<c>/<c>.pq  │
                                │  combined/all_world.pq  │
                                │  sample/sample_map.jsonl │
                                │  preview/map_preview.png │
                                │  splits/split_manifest  │
                                │  manifest.json, README   │
                                └──────────────────────────┘
                                            │
                                            │ upload_to_hf.py
                                            ▼
                                    ┌─────────────────┐
                                    │ HuggingFace     │
                                    │ NoeFlandre/...  │
                                    └─────────────────┘
```

The 7 layers, top-to-bottom:

1. **Source PBFs** (`raw/`): Geofabrik regional extracts (~16 GB
   for the 77-country dataset).
2. **Stage 0 output** (`processed/<country>/01_extracted.jsonl`):
   one JSONL record per polygon with raw OSM tags + geometry.
3. **Stage 2 output** (`02_filtered.jsonl`): subset that hit the
   22,075-tag whitelist.
4. **Stage 3 output** (`03_classified.jsonl`): subset that survived
   the size filter (0.1-100 km²) and got continent + size_bin tags.
5. **Per-country parquet** (`dataset/per_country/<c>/<c>.parquet`):
   one zstd-compressed parquet per country.
6. **Combined parquet** (`dataset/combined/all_world.parquet`):
   all countries concatenated + a `split` column.
7. **HuggingFace** (`NoeFlandre/osm-polygon-selection`): final
   publication.

---

## 2. Module-by-module

### `src/osm_polygon_selection/paths.py`

Tiny module that resolves `OSM_DATASET_DIR` (or defaults to a
sibling-of-project-root path). Both `OSM_DATA_ROOT` and
`OSM_DATASET_DIR` must be set to the HDD for production runs;
see `docs/AGENT_HANDOFF.md` for the policy.

```python
def dataset_root() -> Path:
    env = os.environ.get("OSM_DATASET_DIR")
    if env:
        return Path(env)
    return project_root().parent / "osm-polygon-selection-dataset"
```

### `src/osm_polygon_selection/pbf_meta.py`

Two responsibilities:

1. `NON_EUROPE_COUNTRIES: dict[str, str]` — maps country slug →
   Geofabrik region (currently `"africa"`). Drives `geofabrik_url()`
   so non-European countries get the right URL.
2. `geofabrik_url(country) -> str` — produces
   `https://download.geofabrik.de/<region>/<country>.html`.

When adding a new African country, append it to the dict (TDD test
in `tests/test_pbf_meta.py`).

### `src/osm_polygon_selection/schema_defs.py`

Defines the **frozen** 13-column parquet schema. Every parquet
write goes through `build_schema()`. Every test asserts on the
exact column order + types (see `test_schema_defs.py`).

Column reference (full table in `README.md`):

| name            | type         | source               |
|-----------------|--------------|----------------------|
| osm_id          | int64        | OSM ID (unique)      |
| osm_type        | string       | "way" or "relation"  |
| centroid_lon    | float64      | Stage 0 / Stage 3    |
| centroid_lat    | float64      | Stage 0 / Stage 3    |
| area_km2        | float64      | Stage 0 (area calc)  |
| tags            | list(string) | OSM tags             |
| matched_tag     | string       | Stage 2 (first whitelist hit) |
| continent       | string       | Stage 3 (Natural Earth lookup) |
| size_bin        | string       | Stage 3 (area bin)   |
| country         | string       | build_dataset (from dir name) |
| extract_status  | string       | build_dataset ("clean" / "killed") |
| pbf_date        | string       | build_dataset (PBF mtime) |
| geometry_wkt    | string       | Stage 0 (WKT string) |

### `src/osm_polygon_selection/stages/extract.py`

Stage 0: PBF → JSONL. Uses the `osmium` C++ extension for fast
streaming. Key features:

- **WAL** (`*.seen_ids`): one ID per line; tracks already-processed
  OSM IDs across runs for resume support.
- **Lon/lat pre-filter**: drops polygons whose centroid is outside
  the bbox defined by the PBF metadata. Skip ~70% of irrelevant
  data.
- **C-level vertex count**: rejects polygons with too few/many
  vertices before round-tripping them through Python.
- **`--limit` + `--max-seconds` caps**: produce clean exits, WAL
  preserved, re-run resumes.

### `src/osm_polygon_selection/stages/whitelist.py`

Stage 1: builds `whitelist.json` from the [osm-stats](https://github.com/NoeFlandre/osm-stats)
CSVs/XLSX. Currently 22,075 OSM `key=value` tags. Rationale in
`docs/whitelist_decisions.md`.

### `src/osm_polygon_selection/stages/filter_by_whitelist.py`

Stage 2: takes `01_extracted.jsonl` + `whitelist.json`, emits
`02_filtered.jsonl` (only polygons whose tags hit the whitelist).

### `src/osm_polygon_selection/stages/classify.py`

Stage 3: takes `02_filtered.jsonl` + Natural Earth admin0
shapefile, emits `03_classified.jsonl` with `continent` (point-in-polygon
on centroid) and `size_bin` (area-based).

### `src/osm_polygon_selection/streaming_writer.py`

`write_jsonl_to_parquet()`: high-throughput JSONL → parquet using
`pa.json` (C-level parser) + zstd level 1. Replaces the older
`pa.Table.from_pylist()` round-trip path which was 3-4x slower.

Key entry point used by `build_dataset.py`.

### `src/osm_polygon_selection/readme_render.py`

Renders the root + per-country + folder READMEs. Two main
functions:

- `build_root_readme(manifest, root) -> str`: full root README.
- `build_country_readme(country_info, ...) -> str`: per-country README.

Templates use Python `str.format()` with named placeholders like
`{n_countries}` and `{n_non_europe}`. When adding a new country
note (blurb for the README), edit `COUNTRY_NOTES` in
`scripts/organize_dataset.py` (which has its own local copy).

### `src/osm_polygon_selection/dataset_layout.py`

Moves flat `dataset/` files into the HF viewer layout:
`per_country/<c>/<c>.parquet`, `combined/all_world.parquet`,
`sample/`, `preview/`. Called by `scripts/organize_dataset.py`.

### `src/osm_polygon_selection/country_table.py`, `sample_table.py`, `git_meta.py`, `extract_status.py`

Small helpers used by `readme_render.py` and the build scripts.

---

## 3. Script-by-script

### `scripts/stage0_extract.py` (Stage 0 CLI)

Thin wrapper over `stages/extract.py::extract()`. Adds `--limit`
and `--max-seconds` argparse arguments.

### `scripts/stage2_filter.py`, `stage3_classify.py`

Thin CLIs. They read paths from CLI args + `whitelist.json` from
`OSM_DATA_ROOT`.

### `scripts/build_dataset.py`

The big one. Walks `processed/<country>/` directories, runs the
streaming writer per country (writes `per_country/<c>/<c>.parquet`
and `all_world.parquet` flat at the dataset root), then
`organize_dataset.py` moves them into the HF viewer layout.

Key behaviors:

- Builds the `manifest.json` from scratch on every run.
- Records killed countries (`extract_status = "killed"`,
  `n_polygons = 0`) when their `01_extracted.jsonl.run.json`
  is missing or zero-yield.
- `n_countries` counts only alive countries.
- Honors `OSM_DATASET_DIR` for output location.

### `scripts/organize_dataset.py`

Three phases:

1. **Layout**: move flat dataset files into `per_country/`,
   `combined/`, `sample/`, `preview/`.
2. **READMEs**: write one per folder + one per country (skips
   killed countries since they have no parquet).
3. **Status line**: counts clean vs killed countries.

### `scripts/sample_for_map.py`

Stratified sampling across all 77 countries: targets 5000 polygons
total (~60-70 per country), proportional to country size with a
floor. Used by the static map preview.

### `scripts/make_split.py`

Train/val/test split. The critical optimization (commit `1edc041`):
per-country parquets are NOT rewritten; only `combined/all_world.parquet`
gets a `split` column. Wall-clock dropped from ~10 min to ~2.5 min.

Key behaviors:

- Deterministic: `(seed=42, country_index, n_rows) -> split assignment`.
- Stratified by country (each country independently assigned).
- Default ratios: 80/10/10.
- Per-country parquets keep no `split` column (only used by tests).

### `scripts/upload_to_hf.py`

TDD-friendly HuggingFace upload. Features:

- `--dry-run` mode (lists files, no upload).
- Smallest-first file ordering.
- Reads token from `HF_TOKEN` env or `~/.cache/huggingface/token`.
- Batched upload with progress.
- Skips files already on HF (uses `list_repo_files`).

### `scripts/visualize.py`, `render_map_screenshot.py`

Map rendering: JSONL → interactive HTML (folium) → static PNG.
Used for the dataset viewer preview thumbnail.

---

## 4. Testing strategy

### Per-stage tests (TDD)

Every pipeline stage has tests in `tests/stages/test_<stage>.py`.
Each stage test pins:

- Output schema (column names + types).
- Specific outputs for known inputs.
- Edge cases (empty input, malformed records).

### Per-script integration tests

Each script has a test in `tests/test_<script>.py`:

- `test_build_dataset.py`: build a tiny dataset, assert structure.
- `test_build_dataset_uses_streaming.py`: pins that
  `build_dataset.py` uses the streaming writer (no pandas
  round-trip).
- `test_make_split.py`: 15 tests including the 3 RED tests for
  the per-country-rewrite skip.
- `test_organize_dataset.py`: layout + READMEs.
- `test_sample_for_map.py`: stratified sampling correctness.
- `test_pbf_meta.py`: NON_EUROPE_COUNTRIES + geofabrik_url.
- `test_readme_render.py`: README content.

### Coverage: 280 tests, 278 passing

The deselect for `TestWallClockCap::test_wall_clock_cap_stops_clean`
is for a pre-existing flaky test that fires SIGALRM at teardown.

---

## 5. End-to-end example: adding Mayotte (commit `9de694a`)

The Mayotte commit is the cleanest reference example. Steps:

1. **TDD test** (`tests/test_pbf_meta.py`):
   ```python
   def test_mayotte_uses_africa_region(self):
       assert geofabrik_url("mayotte") == (
           "https://download.geofabrik.de/africa/mayotte.html"
       )
   ```

2. **Add to NON_EUROPE_COUNTRIES** (`src/osm_polygon_selection/pbf_meta.py`).

3. **Add COUNTRY_NOTES** blurb (`scripts/organize_dataset.py`).

4. **Download PBF** to HDD raw/:
   ```bash
   curl -L -o /Volumes/Seagate\ M3/osm-polygon-selection/raw/mayotte-latest.osm.pbf \
     https://download.geofabrik.de/africa/mayotte-latest.osm.pbf
   ```

5. **Stage 0** (15.8s, 805 polygons):
   ```bash
   OSM_DATA_ROOT=/Volumes/Seagate\ M3/osm-polygon-selection \
     uv run scripts/stage0_extract.py \
       /Volumes/Seagate\ M3/osm-polygon-selection/raw/mayotte-latest.osm.pbf \
       /Volumes/Seagate\ M3/osm-polygon-selection/processed/mayotte/01_extracted.jsonl
   ```

6. **Stages 2 + 3** (1s total, 606 polygons).

7. **build_dataset** (8 min): picks up mayotte from processed/,
   writes `mayotte.parquet` + rebuilds combined parquet + manifest.

8. **organize_dataset** (30s): moves new files into HF viewer layout.

9. **sample_for_map** (10s): adds mayotte samples to the map JSONL.

10. **make_split** (2.5 min): rebuilds combined parquet with `split`
    column (deterministic from `(seed=42, country_index=76, n_rows=606)`).

11. **render_map** (2 min): re-renders map_preview.png.

12. **upload_to_hf** (~10 min): 165 files pushed.

13. **commit + push to github**.

Total wall-clock: ~25 min for a small country.

---

## 6. Why this architecture?

A few key decisions and their rationale:

### Why 3 separate stages (0, 2, 3)?

- **Resumability**: each stage has its own WAL + run.json; partial
  failures are localized.
- **Debuggability**: easy to inspect `02_filtered.jsonl` to see what
  the whitelist filter dropped.
- **Cost asymmetry**: stage 0 is the only stage that hits osmium's
  C++ index; stages 2 + 3 are pure Python and run in seconds.

### Why parquet + zstd level 1?

- **Compression**: 36% smaller than snappy for OSM tag data.
- **HF viewer**: row group size 50k keeps each group under 300 MB
  (HF viewer's per-row-group scan limit).
- **Streaming**: `pa.json` + `ParquetWriter.write_batch` lets us
  write a 6 GB combined parquet with O(ROW_GROUP_SIZE) memory.

### Why split by country, not by polygon?

- **Geographic coverage**: ensures train/val/test have similar
  geographic distributions.
- **Generalization test**: a model trained on 80% of countries can
  be evaluated on the held-out 20% to test cross-country
  generalization.

### Why no per-country parquet `split` column?

- **Performance**: skipping the per-country rewrites dropped
  `make_split.py` from ~10 min to ~2.5 min.
- **Single source of truth**: only `combined/all_world.parquet`
  has splits; per-country parquets are pure data.
- **Deterministic reconstruction**: given `(seed, country_index,
  n_rows)`, splits are reproducible.

### Why commit `.claude.md` to git but gitignored it?

Because the user wants the conventions to survive a fresh session
but doesn't want them in the public repo. The gitignored file
holds **operational** rules (storage policy, TDD workflow), not
project documentation. Documentation goes in `docs/`.

# Agent Handoff — conventions, gotchas, accumulated knowledge

This document is the **first thing** a fresh Droid session should
read. It captures everything that took months of trial and error
to learn: storage policy, TDD workflow, project-specific
conventions, common pitfalls, and the state of in-progress work.

If you only read one document, read this one.

---

## 1. Storage policy (CRITICAL — read this first)

**Always use the external HDD, never the MacBook's local storage.**

The user's MacBook SSD has limited space (~46 GiB free at last
check). The pipeline writes 5-7 GB of intermediate parquet files
per build; if any of that lands on the local SSD, the user runs
out of disk space. This has already happened once during the
Africa rollout (cleaned up by deleting 14 GB of stale
`data/dataset/`).

### Hard rules

1. **Always export both env vars** before running any pipeline script:
   ```bash
   export OSM_DATA_ROOT="/Volumes/Seagate M3/osm-polygon-selection"
   export OSM_DATASET_DIR="/Volumes/Seagate M3/osm-polygon-selection/dataset"
   ```
   - `OSM_DATA_ROOT` is read by `stage0_extract.py`, `stage2_filter.py`,
     `stage3_classify.py` (for `whitelist.json`).
   - `OSM_DATASET_DIR` is read by `build_dataset.py`,
     `organize_dataset.py`, `sample_for_map.py`, `make_split.py`,
     `upload_to_hf.py` (via `osm_polygon_selection.paths.dataset_root`).
   - Without either, scripts fall back to a sibling path off the
     project root (e.g. `~/osm-polygon-selection-dataset/` or
     `data/dataset/`), which fills up the SSD.

2. **Never** write pipeline outputs to `/Users/noeflandre/osm-polygon-selection/data/`.
   `data/` is `.gitignore`d but still lives on the local SSD.

3. **After every commit**, verify:
   ```bash
   du -sh /Users/noeflandre/osm-polygon-selection/data   # must be < 100 MB
   du -sh /Volumes/Seagate\ M3/osm-polygon-selection    # ~200 GB, that's fine
   ```

4. **If you accidentally created** `~/osm-polygon-selection-dataset/` or
   any local `data/dataset/`, `rm -rf` it after verifying the HDD has
   the up-to-date copies.

The `scripts/upload_to_hf.py` also reads from `OSM_DATASET_DIR`.

---

## 2. TDD red-green-modular (mandatory for any code change)

Every feature, bugfix, and optimization in this codebase followed
the same TDD loop:

1. **RED**: write a failing test that pins the new contract.
   - Run `uv run pytest tests/test_X.py -k new_test` and confirm it fails.
   - Tests live in `tests/` mirroring `src/` and `scripts/`.
   - One test per behavior; small + focused.

2. **GREEN**: implement the minimum code to make the test pass.
   - Prefer pure functions over I/O so they're trivially testable.
   - Reuse existing helpers (e.g. `assign_split_for_country`,
     `_WHITELIST_CACHE`, `dataset_root`).

3. **VERIFY**: run the full suite, must stay ≥ 278 passing.
   ```bash
   uv run pytest tests/ \
     --deselect tests/stages/test_extract_perf.py::TestWallClockCap::test_wall_clock_cap_stops_clean
   ```

4. **BENCH** (if it's a perf change): measure wall-clock before/after
   on the real dataset.

5. **COMMIT**: `<type>(<scope>): <summary>` with a long body listing
   wall-clock numbers, file counts, polygon counts, and TDD test
   names. Examples in git log:
   - `perf(make_split): skip per-country parquet rewrites (TDD red-green)`
   - `feat(morocco): add Morocco + non-European country support`
   - `feat(tunisia): add Tunisia + second North-African country`

6. **PUSH**: `git push origin main`.

7. **UPLOAD to HF**: `uv run scripts/upload_to_hf.py`.

Commit messages have a long body listing wall-clock numbers, file
counts, polygon counts, and TDD test names. This is for the user's
later review — don't skip it.

### Why this matters

Without the TDD loop the codebase would have suffered from the same
problems that plagued the early days (silent fallback paths, dead
columns, race conditions). The 280 tests are a safety net — never
delete a test to make code "work"; fix the code.

---

## 3. Project conventions

### Code style

- **Pure functions where possible**, I/O at the edges.
- **Docstrings** on every module + every public function. State the
  invariants in plain English.
- **No emoji in code or replies** unless the user requests them.
- **No em dashes** in prose / docs (commas or periods preferred).
- **`pathlib.Path`** everywhere, not `os.path`.
- **`pyarrow`** for parquet, **never** pandas for writing
  (pandas round-trips types in surprising ways).
- **`zstd` level 1** for parquet compression (matches the streaming
  writer's default; ~36% smaller than snappy at ~12% slower encode).
- **`ROW_GROUP_SIZE = 50_000`** for parquet writes (HF viewer wants
  < 300 MB per row group; 50k rows ≈ 50-60 MB).

### Naming

- Per-country slug: kebab-case (e.g. `united-kingdom`,
  `bosnia-herzegovina`, `sao-tome-and-principe`).
- Per-country folder: `per_country/<slug>/<slug>.parquet`.
- Per-country README: `per_country/<slug>/README.md`.
- Combined parquet: `combined/all_europe.parquet` (the name is
  historical; it now also includes African countries).
- Manifest: `dataset/manifest.json` (machine-readable, every build).
- Root README: `dataset/README.md` (human-readable, every build).

### Schema (frozen columns)

Every parquet row has exactly these 13 columns (in order):

| name            | type         |
|-----------------|--------------|
| osm_id          | int64        |
| osm_type        | string       |
| centroid_lon    | float64      |
| centroid_lat    | float64      |
| area_km2        | float64      |
| tags            | list(string) |
| matched_tag     | string       |
| continent       | string       |
| size_bin        | string       |
| country         | string       |
| extract_status  | string       |
| pbf_date        | string       |
| geometry_wkt    | string       |

Plus the trailing `split` column on `combined/all_europe.parquet`
only (`"train"` | `"val"` | `"test"`).

Don't add columns without updating `schema_defs.py` and the
matching test (`test_schema_defs.py`).

### Env var resolution

`src/osm_polygon_selection/paths.py::dataset_root()`:

```python
env = os.environ.get(DATASET_ROOT_ENV)
if env:
    return Path(env)
return project_root().parent / "osm-polygon-selection-dataset"
```

**Implication**: if you forget to set `OSM_DATASET_DIR`, output
goes to `~/osm-polygon-selection-dataset/` (off the project root),
NOT to the local repo. Either way it's wrong (lives on SSD).

---

## 4. Common pitfalls

### The `data/dataset/` duplicate

The local repo's `data/` is `.gitignore`d but not removed. If a
script defaults to writing there (e.g. older versions of
`build_dataset.py` did), you end up with a 14 GB stale copy on
the SSD. Always verify the env vars are set BEFORE running build
or split.

### The per-country parquet `split` column

`make_split.py` does NOT rewrite per-country parquets anymore
(perf optimization in commit `1edc041`). Per-country parquets have
no `split` column; only `combined/all_europe.parquet` has one.

If you see a per-country parquet with a `split` column, it's from
a pre-optimization build. The optimization dropped `make_split.py`
wall-clock from ~10 min to ~2.5 min on the 52-country dataset.

### The `n_countries` count

`manifest.json`'s `n_countries` counts only **alive** countries
(`n_polygons > 0`). Killed countries (`extract_status == "killed"`,
`n_polygons == 0`) are still listed in `manifest.countries` so
downstream users can see they were tried, but excluded from the
count.

### The `make_split` not respecting `n_countries`

`make_split.py` prints `n_countries` but counts ALL countries in
the manifest (alive + killed). Killed countries contribute
`{"train":0,"val":0,"test":0}` to `per_country_counts`. The CLI
n_countries print is filtered to alive only (commit `e251cdb`).

### The `concatenate_me` order

`combined/all_europe.parquet` is built in **manifest order**, which
is the alphabetical/iteration order of `processed/` subdirs. The
`split` column assignment is per-country, deterministic from
`(country_index, seed, n_rows)`. So row order changes if you
re-order processed/. Don't re-order between builds.

### The `--max-seconds` cap

`stage0_extract.py` has `--max-seconds` for huge PBFs (Nigeria
678 MB, France 4.7 GB) whose osmium index build can take 30+ min
and produces no polygons until it finishes. The cap produces a
clean exit (preserves WAL) so you can re-run with no cap (or
higher) to resume.

If a stage 0 run was interrupted mid-extract (e.g. user cancel),
the WAL (`*.seen_ids`) preserves all already-seen IDs. Just re-run
without `--max-seconds` and it picks up where it left off.

### The `row offset` mismatch in `make_split`

When `_write_combined_streaming` reads per-country parquets row
group by row group, the splits array is computed for the whole
country at once. The `row_offset` variable tracks the cumulative
position within the country across row groups. Don't refactor that
without running `test_make_split.py`.

---

## 5. State of in-progress work

### Africa rollout (commit `e251cdb` + `9de694a`)

Currently **77 of 55** African countries done... wait, 28 of 55.
Africa has ~55 countries in Geofabrik's `/africa/` subtree. **28
are processed** (3 prior: morocco, tunisia, algeria; 24 from
batch 1+2: sao-tome-and-principe, comores, seychelles,
saint-helena-ascension-and-tristan-da-cunha, equatorial-guinea,
djibouti, mauritius, guinea-bissau, cape-verde, gabon,
congo-brazzaville, burundi, sierra-leone, benin, liberia, namibia,
rwanda, togo, libya, niger, swaziland, eritrea, mauritania,
canary-islands; 1 most recent: mayotte). **26 remaining** (the
larger PBFs: Nigeria, Tanzania, South Africa, DRC, Uganda, Kenya,
Mozambique, Zambia, Cameroon, Sudan, Zimbabwe, Egypt, Mali,
Somalia, Malawi, Ethiopia, South Sudan, Chad, Lesotho, Angola,
Botswana, CAR, Burkina Faso, Ivory Coast, Ghana, Guinea,
Senegal+Gambia). Their PBFs are downloaded in `raw/` but stage 0
was interrupted; `processed/<country>/` dirs were cleaned up.

See `docs/AFRICA_ROLLOUT.md` for the full queue + resume plan.

### TDD plans pending

- **make_split.py: skip per-country rewrites** ✅ DONE (commit `1edc041`).
- Further make_split optimizations on the table (e.g. parallel
  per-country reads, but small marginal wins).

### Known flaky test

`tests/stages/test_extract_perf.py::TestWallClockCap::test_wall_clock_cap_stops_clean`
sometimes fails with a `SIGALRM at test teardown` error. This is
pre-existing, unrelated to the dataset work, and is excluded from
the test runs via `--deselect`. If you fix it, great; if not,
keep the deselect.

---

## 6. Performance benchmarks

Wall-clock for the full rebuild on the 77-country dataset:

| Step                         | Wall-clock |
|------------------------------|-----------:|
| Stage 0 (per country)        |   5-400 s  |
| Stage 2 + 3 (per country)    |    1-3 s   |
| build_dataset.py             |   8-12 m   |
| organize_dataset.py          |  ~30-60 s  |
| sample_for_map.py            |    ~10 s   |
| make_split.py                |  ~2.5 m    |
| HF upload (165 files)        |  ~7-12 m   |
| **Total per country** (med)  |  ~10-15 m  |

make_split went from ~10 min to ~2.5 min in commit `1edc041`
(skip per-country parquet rewrites — the per-country file doesn't
need a `split` column; only `combined/all_europe.parquet` is used
for training).

Stage 0 perf for large PBFs:
- France 4.7 GB: ~30 min (was killed before; now OK with
  `--max-seconds` cap + resume).
- Nigeria 678 MB: ~10-15 min.
- Tanzania 671 MB: ~10-15 min.

See `docs/PERFORMANCE.md` for the full history of optimizations.

---

## 7. HuggingFace upload gotchas

- `upload_to_hf.py` reads token from `HF_TOKEN` env var or
  `~/.cache/huggingface/token`.
- `--dry-run` mode shows what would be uploaded without pushing.
- Files are ordered smallest-first so the dataset page populates
  quickly while big combined parquet uploads.
- `.DS_Store` files in the dataset dir sometimes get uploaded
  accidentally — delete them via `api.delete_file()` after upload.
- The dataset name is `NoeFlandre/osm-polygon-selection` (type: `dataset`).

---

## 8. What NOT to do

- **Don't** run 27 `stage0_extract.py` in parallel — it hammers
  the HDD and slows everything down. 2-3 parallel is fine.
- **Don't** commit the `data/dataset/` (or `~/osm-polygon-selection-dataset/`)
  contents — they're gitignored and live on the wrong disk.
- **Don't** delete a test to make code "work" — fix the code instead.
- **Don't** skip the TDD loop "just this once" — the codebase
  regresses fast without it.
- **Don't** add a column to the parquet schema without updating
  `schema_defs.py` AND the test.
- **Don't** use `os.path` — use `pathlib.Path`.
- **Don't** write parquet with snappy — use zstd level 1.
- **Don't** re-order `processed/<country>/` dirs between builds
  (changes combined parquet row order → changes split column).

---

## 9. Quick reference: the most important files

| File                                             | Why it matters                                   |
|--------------------------------------------------|--------------------------------------------------|
| `.claude.md`                                     | Local agent memory (gitignored, this is the source of truth for the HDD policy) |
| `src/osm_polygon_selection/paths.py`             | Where the env var resolution happens            |
| `src/osm_polygon_selection/pbf_meta.py`          | `NON_EUROPE_COUNTRIES` + `geofabrik_url()`       |
| `src/osm_polygon_selection/readme_render.py`     | Root + per-country README rendering (templates)  |
| `src/osm_polygon_selection/schema_defs.py`       | Frozen parquet schema                            |
| `scripts/make_split.py`                          | train/val/test split (now skipping per-country rewrites) |
| `scripts/build_dataset.py`                       | Build the parquet dataset                        |
| `scripts/organize_dataset.py`                    | Move flat dataset/ to HF viewer layout           |
| `scripts/upload_to_hf.py`                        | Push to HuggingFace                              |
| `docs/dataset_state.md`                          | Live state doc (rebuilt every commit)            |
| `docs/ARCHITECTURE.md`                           | Deep dive on modules                             |
| `docs/PERFORMANCE.md`                            | Benchmarks                                       |
| `docs/AFRICA_ROLLOUT.md`                         | Africa loop status                               |

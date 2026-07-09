# Performance — benchmarks + optimizations applied

This document captures the wall-clock numbers for each pipeline
step on the real 77-country dataset, and the optimizations that
got us here.

For conventions + storage policy, see `docs/internal/AGENT_HANDOFF.md`.
For architectural details, see `docs/architecture.md`.

---

## Current numbers (77-country dataset, July 2026)

| Step                        | Wall-clock | Memory    | Notes                              |
|-----------------------------|-----------:|-----------|------------------------------------|
| Stage 0 (per country, tiny) |    5-15 s  | ~400 MB   | Saint-Helena 848 KB: 5 s           |
| Stage 0 (per country, med)  |  200-400 s | ~1.5 GB   | Algeria 284 MB: 398 s              |
| Stage 0 (per country, large)|  10-30 min | ~2 GB     | France 4.7 GB: ~30 min             |
| Stage 2 + 3 (per country)   |     1-3 s  | ~50 MB    | Pure Python, vectorized            |
| build_dataset.py            |   8-12 min | O(chunk)  | Streaming writer + pa.json         |
| organize_dataset.py         |   30-60 s  | <100 MB   | File moves + README writes         |
| sample_for_map.py           |    ~10 s   | ~500 MB   | Stratified sample, 5000 rows      |
| make_split.py               |   ~2.5 min | ~200 MB   | Skips per-country rewrites (TDD)   |
| visualize.py                |     ~30 s  | ~500 MB   | folium HTML render                 |
| render_map_screenshot.py    |     ~60 s  | ~200 MB   | headless chromium                  |
| upload_to_hf.py (165 files) |   7-12 min | <200 MB   | Smallest-first ordering            |
| **Total per country** (med) |  ~10-15 m  |           |                                    |

---

## The 22-min rebuild problem (the big win)

Before the optimizations, adding a new country to the dataset
cost **~22 minutes of rebuild time**:

| Step                  | Wall-clock (before) | Wall-clock (after) |
|-----------------------|--------------------:|-------------------:|
| build_dataset.py      |              ~12 m  |            ~12 m   |
| make_split.py         |              ~10 m  |           ~2.5 m   |
| **Total**             |              ~22 m  |          **~15 m** |

The `make_split.py` savings came from commit `1edc041` (TDD
red-green, see `docs/internal/AGENT_HANDOFF.md` for the workflow).

### Why was make_split so slow?

It rewrote **every** per-country parquet (51 files, 10k-1.3M rows
each) just to append a `split` column. That's ~7.4M rows round-tripped
through `ParquetWriter.write_table()` for no good reason — the
per-country file is never used for training (only `combined/all_world.parquet`
is).

### The optimization

1. **RED test**: 3 new tests in `tests/splitting/test_per_country.py`:
   - `test_per_country_parquets_not_rewritten_after_split`
     (mtime check).
   - `test_per_country_parquets_have_no_split_column_after_split`
     (schema check).
   - `test_combined_parquet_has_split_column_after_split`
     (correctness check).

2. **GREEN**: refactored `make_split()` to:
   - Pre-compute splits per country from `(seed, country_index,
     n_rows)` — deterministic.
   - Skip per-country parquet rewrites entirely.
   - Pass seed + ratios + manifest into
     `_write_combined_streaming()`.
   - Make `_write_combined_streaming()` append `split` on-the-fly
     to each row group.
   - Strip any legacy `split` column from per-country parquets
     (from previous runs) so the combined output has exactly one
     `split` column, not two.

3. **Correctness verified** via full diff against previous output:
   - Rows: 7,353,903 → 7,353,903.
   - Schema: 14 columns, no duplicates.
   - Row order: identical.
   - Splits: **0 differences** across 7.3M rows.

### Updated existing tests

The 4 tests that previously read the `split` column from per-country
parquets were updated to read from the combined parquet instead:

- `test_split_assigns_all_rows`
- `test_split_is_deterministic`
- `test_split_different_seeds_differ`
- `test_split_writes_split_column_to_parquet`

This is a deliberate **test contract change**: per-country parquets
no longer have a `split` column. Only `combined/all_world.parquet`
has one.

---

## Earlier optimizations (still in effect)

### Stage 0 — fast lon/lat area pre-filter (commit `0510996`)

Before: every OSM object in the PBF was round-tripped through
Python just to check if it was a polygon with a valid area.

After: a C-level pre-filter on the bounding-box header of the PBF
drops ~70% of irrelevant data (objects whose lon/lat is outside
the PBF's bbox). Wall-clock for stage 0 dropped 2-3x on big PBFs.

### Stage 0 — C-level vertex count (commit `0510996`)

Before: Python counted vertices for every polygon.

After: osmium's C++ extension counts vertices during the streaming
pass. Polygons with too few (probably malformed) or too many
(multipolygons with millions of vertices) are rejected before
Python sees them.

### build_dataset.py — pa.json C-level parser (commit `fd39de2`)

Before: `pa.Table.from_pylist(rows)` round-tripped every row
through Python objects.

After: `pa.json.read_json()` parses each row at the C level,
keeping the streaming writer's memory footprint bounded by
`ROW_GROUP_SIZE` instead of `len(rows)`.

### build_dataset.py — streaming JSONL → parquet writer (commit `2b1b773`)

Before: loaded the whole JSONL into a Python list, then converted
to a pyarrow table.

After: `streaming_writer.write_jsonl_to_parquet()` reads the JSONL
row-by-row, batches them into `ROW_GROUP_SIZE` chunks, and writes
each chunk via `ParquetWriter.write_batch()`. Memory stays O(chunk)
instead of O(table).

### zstd compression (commit `7380f95`)

Before: combined parquet used snappy (~9.4 GB for 7.3M rows).

After: combined parquet uses zstd level 1 (~6.0 GB for 7.3M rows).
**36% smaller** at ~12% slower encode. Well worth it.

---

## Per-country stage 0 timings (real measurements)

| Country                  | PBF size | Stage 0 wall-clock | Polygons |
|--------------------------|---------:|-------------------:|---------:|
| Saint-Helena (... Cunha) |    848 K |               5 s  |      177 |
| Sao Tome and Principe    |    1.2 M |              9 s   |      208 |
| Seychelles               |    2.6 M |             17 s   |      314 |
| Comores                  |    3.8 M |             28 s   |      455 |
| Mauritius                |    9.0 M |             37 s   |    2,120 |
| Equatorial Guinea        |    6.2 M |             39 s   |    1,009 |
| Djibouti                 |    6.7 M |             40 s   |      582 |
| Guinea-Bissau            |   10.6 M |             41 s   |    2,118 |
| Cape Verde               |   11.1 M |             92 s   |    2,472 |
| Eritrea                  |   29.5 M |            336 s   |    3,294 |
| Gabon                    |   24.1 M |            440 s   |    3,857 |
| Mauritania               |   28.9 M |            478 s   |    9,179 |
| Swaziland                |   29.1 M |            514 s   |    4,119 |
| Canary Islands           |   56.0 M |            524 s   |    2,706 |
| Congo-Brazzaville        |   30.7 M |            570 s   |    6,705 |
| Liberia                  |   35.5 M |            592 s   |    2,485 |
| Namibia                  |   51.0 M |            590 s   |    9,454 |
| Burundi                  |   44.0 M |            609 s   |    4,678 |
| Sierra Leone             |   40.7 M |            604 s   |    3,448 |
| Benin                    |   45.5 M |            671 s   |    4,659 |
| Tunisia                  |   79.0 M |            135 s   |   10,290 |
| Togo                     |   59.0 M |            767 s   |    3,436 |
| Rwanda                   |   62.0 M |            764 s   |    4,373 |
| Libya                    |   72.0 M |            748 s   |   13,158 |
| Niger                    |   71.0 M |            781 s   |   14,769 |
| Morocco                  |  231.0 M |            201 s   |   43,531 |
| Algeria                  |  284.0 M |            398 s   |   33,183 |
| Mayotte                  |   10.0 M |             16 s   |      805 |

(Variance is mostly due to OSM object density, not just PBF size.
Algeria takes 398 s for 284 MB; Morocco takes 201 s for 231 MB —
Morocco has a denser urban mesh.)

---

## Things we tried that didn't help (or hurt)

### Pandas for parquet writes

`pd.DataFrame.to_parquet()` is slower than `pq.write_table()` and
silently drops nullable metadata. Don't use it.

### Parallel stage 0 runs

Running 27 `stage0_extract.py` in parallel for the Africa rollout
(commit `e251cdb`) **saturated the HDD** and the entire machine
became unresponsive. The user had to interrupt. **Lesson: 2-3
parallel stage 0 is fine; more than that hammers the disk.**

### More than 8 GB heap

Trying to hold the full combined parquet in memory before writing
(zstd, OOM at ~6M rows). The streaming writer exists exactly
because of this.

### Re-reading per-country parquets for `split` injection

That's the old slow path. The fix is in commit `1edc041`.

---

## Future optimization ideas

(Not yet implemented; tracked in `docs/internal/AGENT_HANDOFF.md`.)

- **Parallel per-country stage 0** with 2-3 workers (already safe
  with the WAL, just need a driver script).
- **Pre-compute per-country splits once** in a manifest, then
  read them in `_write_combined_streaming()` (avoids the
  `assign_split_for_country()` call per row group).
- **Skip `combined/all_world.parquet` rewrite entirely** if no
  new countries were added (already partly done by checking
  mtimes, but not optimized).

The current 22-min → 15-min improvement is the easy 30%; the
remaining 13 min is mostly stage 0 for big PBFs (Nigeria 678 MB,
Tanzania 671 MB, etc.) which is bound by the osmium index build.

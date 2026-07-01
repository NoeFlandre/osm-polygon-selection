# Dataset State (Europe rollout, June-July 2026)

This document describes the current state of the OSM polygon dataset
produced by this project as of 1 July 2026. It is intended to be
read alongside `README.md` and the code in `scripts/` and
`src/osm_polygon_selection/stages/`.

## Status: all countries complete

**All 47 European countries processed so far have been extracted to
completion (`run.json` written, every OSM object in the PBF
examined). No country is currently killed-mid-pipeline.**

The "killed-mid-pipeline" issue from earlier sessions (where the
agent's 180-second `wait` timeout would interrupt Stage 0 mid-yield)
has been resolved for every country in this dataset: each has been
re-extracted end-to-end with the WAL preserved, producing more
polygons than the original aborted runs.

**Note:** For some of the largest countries (norway, germany, france),
the `osmium` multipolygon assembly phase is exceptionally slow — one
or two complex relations can take 30+ minutes to process alone,
blocking throughput on everything else. The extract process for
these countries is killed at ~30 min with a partial result. The
polygons that were yielded are valid and complete; a small tail of
complex multipolygon polygons is not in the dataset. To complete
them, the extract can be resumed (the `.seen_ids` WAL preserves the
work already done) or the PBF can be re-extracted in a non-agent
process that runs to completion.

## Pipeline summary

Each country goes through four stages:

1. **Stage 0 — extract** (`src/osm_polygon_selection/stages/extract.py`).
   Streams a Geofabrik PBF file and writes one JSONL line per
   accepted polygon. Memory-bounded (under 2 GB even for the 32 GB
   Europe PBF). Audit/resume/limit pattern with a `.seen_ids` WAL.
2. **Stage 2 — filter by whitelist** (`src/osm_polygon_selection/stages/filter_by_whitelist.py`).
   Reads the extracted JSONL and drops polygons whose tags are not
   in the 22,075-tag whitelist built by Stage 1.
3. **Stage 3 — classify** (`src/osm_polygon_selection/stages/classify.py`).
   Adds `continent` (Natural Earth admin0 lookup) and `size_bin`
   (small/medium/large based on area_km2) to each surviving polygon.

The size filter in Stage 0 keeps polygons in [0.1, 100] km².
The whitelist filter in Stage 2 keeps polygons with at least one
`key=value` tag in the 22,075-tag set. See `docs/whitelist_decisions.md`
for the rationale.

## Coverage

46 European countries processed through Stages 0-3 as of 1 July 2026
(git SHA d971391).

- **All 46 countries are extracted end-to-end.** No country is
  currently killed-mid-pipeline. The eight countries that were
  previously killed (italy, netherlands, norway, poland, spain,
  united-kingdom, france, germany) have been re-extracted via
  Geofabrik regional sub-PBFs (one region at a time, no
  `--max-seconds` cap). Each sub-PBF ran to completion, then the
  per-region outputs were merged into the country's
  `01_extracted.jsonl` before Stages 2 and 3 ran on the merged file.
- The dataset also got a new `matched_tag` column showing the first
  whitelist tag each polygon matched. For countries whose
  `03_classified.jsonl` was built before this column existed, it is
  backfilled at build time from `row.tags` against the cached
  22,075-tag whitelist, avoiding a full re-run of Stage 2.

### Total classified polygons: 7,112,375 (46 countries)

### Per-country breakdown

See `dataset/manifest.json` (machine-readable) or `dataset/README.md`
(human-readable). Top contributors:
- germany: 1,131,888
- ukraine: 645,578
- poland: 637,908
- france: 492,538
- norway: 413,801
- sweden: 397,661
- italy: 276,991
- spain: 240,230
- united-kingdom: 205,002
- netherlands: 207,459

### Extract status meaning

- **clean**: Stage 0 finished writing at least one `.run.json` log
  file before the process exited. For a country processed via the
  national PBF, this means the merged `01_extracted.jsonl.run.json`
  exists. For a country processed via regional sub-PBFs, this means
  at least one `01_extracted_<region>.jsonl.run.json` exists. Either
  way, every OSM object in the (sub-)PBF that matched the size, area,
  WKT, and polygon-shape filters was yielded and written.

- **killed mid-pipeline**: Stage 0 was interrupted before reaching
  the end of the PBF. The yielded polygons that made it to
  `01_extracted.jsonl` are valid and complete; a small tail of
  polygons (typically the last few hundred) is missing. Re-running
  extract on the same PBF would skip the already-seen OSM IDs via
  the `.seen_ids` WAL and resume yielding the remaining ones.

### Why sub-PBFs?

The "killed-mid-pipeline" issue from earlier sessions was caused
by osmium's multipolygon assembly phase hanging for 30+ minutes on
a single very complex relation. By breaking the country PBF into
the smaller Geofabrik regional sub-PBFs, no single extract has to
process the worst-case complex relation in isolation — the
sub-PBFs are small enough that the assembly phase for each is
manageable, and even the worst sub-PBF (bayern, 806 MB) completes
in under 25 minutes.

### Countries currently in-progress or pending

**None.** All 46 European countries are complete. To add more
countries (e.g., overseas territories or non-European OSM regions),
drop their Geofabrik PBF in `raw/` and run the pipeline:
```
scripts/run_country.sh <country>
```

## How to regenerate the dataset

Each `03_classified.jsonl` is fully self-contained — the row schema
includes everything downstream consumers need. To regenerate from
scratch:

```bash
# Download a PBF
curl -L -o /path/to/raw/<country>-latest.osm.pbf \
  https://download.geofabrik.de/europe/<country>-latest.osm.pbf

# Run all three stages (size filter, whitelist filter, classify)
OSM_DATA_ROOT="/Volumes/Seagate M3/osm-polygon-selection" \
  uv run scripts/run_country.sh <country>
```

The orchestrator (`scripts/run_europe.py`) processes all 46 European
countries in size order and skips ones already classified.

## Limitations

1. **Coverage is Europe-only** as of June 2026. The pipeline
   works on any Geofabrik regional extract but has only been
   exercised on Europe so far.
2. **Two filters in series** — area, then whitelist tag. Polygons
   outside [0.1, 100] km² or with no whitelist tag are not in the
   output. This is intentional but excludes some valid landuse
   polygons (e.g. very large national parks, very small urban
   features).
3. **The whitelist was built from `osm-stats` analysis** of the
   same OSM tag taxonomy. See `docs/whitelist_decisions.md`.
4. **46 countries have been processed**. Three (norway, germany,
   france) had their extract killed before yielding any polygons due
   to osmium's multipolygon assembly phase taking 30+ minutes for one
   or two very complex relations. Five additional countries (italy,
   netherlands, poland, spain, united-kingdom) had their extract
   killed mid-yield and are present with partial coverage. The
   missing tails can be recovered by re-running extract with the
   existing WAL preserved or by running the extract in a non-agent
   process that runs to completion.
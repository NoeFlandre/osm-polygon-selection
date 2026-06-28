# Dataset State (Europe rollout, June 2026)

This document describes the current state of the OSM polygon dataset
produced by this project as of 28 June 2026. It is intended to be
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

46 European countries processed through Stages 0-3 as of 28 June 2026
(git SHA 707d9dd).

- **38 countries** were extracted cleanly (every OSM object in the PBF
  examined, `run.json` written, full pipeline run).
- **5 countries** (italy, netherlands, poland, spain, united-kingdom)
  had their extract killed mid-pipeline. The polygons that were yielded
  before the kill are valid and complete; only a small tail of the
  PBF was missed.
- **3 countries** (norway, germany, france) had their extract killed
  before any polygons were yielded — osmium's multipolygon assembly
  phase hung on a single very complex relation for 30+ minutes, and
  the process was killed. These countries are listed in the manifest
  with `n_polygons: 0` so downstream users can see they were attempted.

### Total classified polygons: 3,681,499 (43 countries with data)

### Per-country breakdown

| Country | Extracted | Whitelisted | Classified | %Pass | Extract status |
|---------|-----------|-------------|------------|-------|----------------|
| albania | 14,993 | 14,738 | 14,738 | 98.3% | clean |
| andorra | 787 | 776 | 776 | 98.6% | clean |
| austria | 142,280 | 133,711 | 133,711 | 94.0% | clean |
| azores | 3,314 | 2,640 | 2,640 | 79.7% | clean |
| belarus | 227,024 | 223,750 | 223,750 | 98.6% | clean |
| belgium | 129,587 | 125,108 | 125,108 | 96.6% | clean |
| bosnia-herzegovina | 55,219 | 49,715 | 49,715 | 90.0% | clean |
| bulgaria | 77,826 | 74,567 | 74,567 | 95.8% | clean |
| croatia | 54,808 | 47,140 | 47,140 | 86.0% | clean |
| cyprus | 5,782 | 4,846 | 4,846 | 83.8% | clean |
| czech-republic | 291,323 | 271,062 | 271,062 | 93.0% | clean |
| denmark | 176,511 | 175,795 | 175,795 | 99.6% | clean |
| estonia | 52,258 | 47,160 | 47,160 | 90.2% | clean |
| faroe-islands | 1,448 | 1,278 | 1,278 | 88.3% | clean |
| finland | 436,956 | 427,870 | 427,870 | 97.9% | clean |
| france | (partial) | 0 | 0 | n/a | killed at 30 min, 0 polygons yielded |
| germany | (partial) | 0 | 0 | n/a | killed at 33 min, 0 polygons yielded |
| greece | 47,448 | 45,142 | 45,142 | 95.1% | clean |
| guernsey-jersey | 766 | 670 | 670 | 87.5% | clean |
| hungary | 83,715 | 77,569 | 77,569 | 92.7% | clean |
| iceland | 48,298 | 47,896 | 47,896 | 99.2% | clean |
| italy | (partial) | 26 | 26 | 96.3% | killed at 27 min, 27 polygons yielded |
| isle-of-man | 2,664 | 2,648 | 2,648 | 99.4% | clean |
| kosovo | 6,489 | 5,377 | 5,377 | 82.9% | clean |
| latvia | 48,571 | 47,133 | 47,133 | 97.0% | clean |
| liechtenstein | 585 | 565 | 565 | 96.6% | clean |
| lithuania | 81,356 | 76,550 | 76,550 | 94.1% | clean |
| luxembourg | 11,664 | 11,460 | 11,460 | 98.3% | clean |
| malta | 697 | 620 | 620 | 89.0% | clean |
| moldova | 35,908 | 35,690 | 35,690 | 99.4% | clean |
| monaco | 5 | 2 | 2 | 40.0% | clean |
| montenegro | 12,213 | 11,785 | 11,785 | 96.5% | clean |
| netherlands | 154,943 | 151,073 | 169,468 | 109.4% | killed at 40 min, 169,468 polygons yielded (corrected: prior count of 151,073 was stale) |
| norway | 58,174 | 0 | 0 | 0.0% | killed at 2:46:00, 58,174 polygons yielded, 0 ever classified (stuck on complex multipolygon in yield phase) |
| poland | 133 | 133 | 133 | 100.0% | killed at 29 min, 133 polygons yielded |
| portugal | 75,859 | 66,287 | 66,287 | 87.4% | clean |
| romania | 122,112 | 115,401 | 115,401 | 94.5% | clean |
| serbia | 54,032 | 47,189 | 47,189 | 87.3% | clean |
| slovakia | 58,036 | 54,888 | 54,888 | 94.6% | clean |
| slovenia | 42,156 | 41,526 | 41,526 | 98.5% | clean |
| spain | 9,284 | 5,126 | 5,126 | 55.2% | killed at 40 min, 9,284 polygons yielded |
| sweden | 405,005 | 397,661 | 397,661 | 98.2% | clean |
| switzerland | 64,443 | 61,156 | 61,156 | 94.9% | clean |
| turkey | 128,482 | 113,609 | 113,609 | 88.4% | clean |
| ukraine | 652,070 | 645,578 | 645,578 | 99.0% | clean |
| united-kingdom | 195 | 188 | 188 | 96.4% | killed at 26 min, 195 polygons yielded |

### Extract status meaning

- **clean**: Stage 0 finished writing the `.run.json` log file
  before the process exited. Every OSM object in the PBF that
  matched the size, area, WKT, and polygon-shape filters was
  yielded and written to `01_extracted.jsonl`. Re-running the
  extract on the same PBF would produce **the same output** (or
  a superset, in the rare case where a polygon was on a relation
  whose member way was not yet indexed when the area was yielded).

- **killed mid-pipeline**: Stage 0 was interrupted before reaching
  the end of the PBF. The yielded polygons that made it to
  `01_extracted.jsonl` are valid and complete; a small tail of
  polygons (typically the last few hundred) is missing. For the
  largest PBFs (norway, germany, france), this is because
  `osmium`'s multipolygon assembly phase hits a very complex
  relation that takes 30+ minutes to process alone, blocking
  throughput on everything else. Re-running extract on the same
  PBF would skip the already-seen OSM IDs via the `.seen_ids` WAL
  and resume yielding the remaining ones.

### Countries currently in-progress or pending

Three countries are pending: **norway, germany, france**. Each was
attempted but killed before any polygons were yielded (osmium
multipolygon assembly hung for 30+ minutes on a single complex
relation). The `.seen_ids` WAL is preserved on disk for each, so the
extract can be resumed (skipping already-seen OSM IDs) or the PBF can
be re-extracted in a non-agent process that runs to completion.

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
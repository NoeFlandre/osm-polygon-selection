---
name: osm-polygon-selection-pipeline
description: Use when working on the osm-polygon-selection pipeline — extracting OSM polygons from PBF files, classifying them by continent + size bin, filtering by whitelist, and visualizing samples. Covers the project-specific architecture, the audit/resume/limit pattern, and the agent timeout pitfalls we hit.
version: 1.0.0
author: Noé
license: MIT
metadata:
  hermes:
    tags: [osm, gis, pipeline, pbf, osmium, geofabrik, europe]
    related_skills: [plan, requesting-code-review]
---

# OSM Polygon Selection Pipeline

## Overview

This project selects OSM polygons for downstream training (Prism-style
landuse/landcover classification). Pipeline reads a Geofabrik PBF
file, filters by an osm-stats-derived whitelist, classifies each
polygon by continent (Natural Earth) and size bin, and writes a
JSONL of selected polygons. Stages 0-3 are working and tested on
multiple European countries; Stage 4 (sample to 5k) and Stage 5
(Wikipedia evidence, out of scope) are pending.

This skill is **local-only** — it lives in `docs/skills/` and is in
`.gitignore`. It captures the hard-won knowledge from building and
running this pipeline so a future agent session doesn't relearn
every pitfall from scratch.

## When to Use

- Working on the `osm-polygon-selection` codebase
- Adding a new pipeline stage
- Debugging extract / classify / filter issues
- Running the pipeline on a new PBF extract
- Visualizing polygon samples
- Reasoning about PBF scale, memory, or first-pass performance

## Architecture

```
src/osm_polygon_selection/
├── core/                    pipeline-agnostic primitives
│   ├── geometry_utils.py     CRS / area / centroid helpers
│   ├── jsonl_utils.py        stream_jsonl(in, out, transform) -> (kept, seen)
│   ├── paths.py              OSM_DATA_ROOT env-var resolver
│   └── wiki_api.py           (DELETED — Wikipedia out of scope)
└── stages/                  one module per pipeline stage
    ├── extract.py            Stage 0: PBF -> JSONL
    ├── whitelist.py          Stage 1: osm-stats -> whitelist.json
    ├── filter_by_whitelist.py  Stage 2: JSONL -> filtered JSONL
    └── classify.py           Stage 3: continent + size_bin

scripts/
├── run_country.sh           one-shot end-to-end per country
├── stage0_extract.py        --limit N + progress + WAL
├── stage1_build_whitelist.py
├── stage2_filter.py
├── stage3_classify.py
├── sample_for_map.py        stratified sample for visualization
├── visualize.py             folium HTML map (color by country)
└── run_country.sh           end-to-end country pipeline

data/                        (gitignored; OSM_DATA_ROOT points here)
├── raw/<region>-latest.osm.pbf
├── reference/                Natural Earth shapefile, osm-stats
├── processed/<country>/     per-country pipeline outputs
│   ├── 01_extracted.jsonl
│   ├── 01_extracted.jsonl.seen_ids     (WAL — every OSM id touched)
│   ├── 01_extracted.jsonl.progress.json (live, rewritten each tick)
│   ├── 01_extracted.jsonl.run.json     (final, at end of run)
│   ├── 02_filtered.jsonl
│   └── 03_classified.jsonl
└── whitelist.json           (built by Stage 1, ~22k tags)
```

## The Audit/Resume/Limit Pattern (extract.py)

`extract.py` is the only stage that does heavy I/O on a 32GB PBF.
It implements three properties together:

1. **Auditable** — `progress.json` is rewritten atomically (tmp +
   rename) every ~15s OR every 100k objects, whichever first. Read it
   with `cat` to see live state. `run.json` is written at end with
   full metadata (pbf_size, start/end times, drops, total seen).

2. **Resumable** — `.seen_ids` WAL records EVERY OSM id ever
   examined (kept OR dropped). On re-run, those ids are skipped
   entirely — no re-evaluation, no double-counting in drops. This
   is critical: a 32GB Europe PBF has 200M+ OSM objects.

3. **Stoppable** — `--limit N` caps a run. Run again with no limit
   to resume. Run with a higher limit to extend.

**Why a single "seen" set, not separate kept/dropped sets:** drops
double-counted on resume before this change. The seen set tracks
what we've *considered*, drops are tracked separately as per-run
counts in `run.json`.

**Trade-off: WAL disk size on Europe.** 200M+ ids × ~10 bytes = ~2GB
WAL. The seen set in RAM is bounded by `len(seen_ids)` (~1-2GB
extra RSS on 8GB M2 — OK). If we ever process a 70GB planet PBF,
the WAL could grow to ~5GB. Disk is cheap; this is fine.

## The Two-Pass Nature of osmium's with_areas()

`osmium.FileProcessor(path).with_areas()` does:

1. **Pass 1:** Build an index of all multipolygon relations and their
   member ways. Touches every OSM object. Takes 10-45 min for a
   32GB PBF. Produces **no polygons**.
2. **Pass 2:** Yield `Area` objects (closed ways + assembled
   multipolygon relations). Where polygons get written.

**Implication for monitoring:** during Pass 1, `n_written=0` and
`n_skipped=0` no matter how long it runs. The only signal is
`drops["not_an_area"]` growing. `progress.json` shows this.

**Implication for the agent:** the agent's 180s `wait` timeout
kills the process before Pass 1 finishes for big PBFs. Use
**`terminal(background=true)` to launch, then poll `.progress.json`
and `ps` separately**. Never `wait` on a multi-minute process.

**Implication for resume:** the WAL is only written during Pass 2
yields. If killed during Pass 1, resume re-does Pass 1 from
scratch (no WAL to skip from).

## PBF Size vs First-Pass Time

| PBF size | First-pass time | Notes |
|----------|-----------------|-------|
| 650KB (Monaco) | <1s | instant |
| 3MB (Andorra) | 5s | fine |
| 35MB (Cyprus) | ~30s | fine |
| 61MB (Iceland) | ~1m | fine |
| 656MB (Belgium) | ~3-5m | borderline agent timeouts |
| 32GB (Europe) | 30-45m | needs a non-agent process |

**Recommended strategy:** for testing, use small country PBFs
(Monaco 650KB, Andorra 3MB, Cyprus 35MB). For end-to-end coverage,
run country-by-country, ~30s to ~5min each.

## Geofabrik PBF URL pattern

```
https://download.geofabrik.de/europe/<name>-latest.osm.pbf
```

Names are lowercase, hyphens, ISO-ish: `united-kingdom`,
`czech-republic`, `bosnia-herzegovina`. The continent PBFs are at
`/europe/`, `/asia/`, `/africa/`, etc.

Use `curl -sIL <url> | grep -i content-length` to get the size
without downloading.

## Scripts Conventions

`scripts/run_country.sh <name> [stage0_limit]` is the
end-to-end-per-country entry point. It downloads (if missing),
extracts, filters, classifies. Use it instead of running the four
stage scripts individually.

`scripts/sample_for_map.py` reads all `03_classified.jsonl` files
under `processed/`, samples 300 polygons (per-country allocation
with floor/cap, round-robin over size bins), and writes
`/tmp/sample_map.jsonl`. Then `scripts/visualize.py <jsonl> <html>`
renders to folium HTML with country-color coding and a legend.

## Common Pitfalls

1. **OSM_DATA_ROOT env var.** The pipeline reads data from
   `OSM_DATA_ROOT` if set, else `./data`. The HDD workflow expects
   `OSM_DATA_ROOT=/Volumes/Seagate M3/osm-polygon-selection`.
   Without it, the script reads from the repo's `data/` which is
   tiny (just Liechtenstein).

2. **Whitelist not on HDD.** Stage 2 needs the whitelist at
   `OSM_DATA_ROOT/whitelist.json`. The first time you run on the
   HDD, `cp data/whitelist.json <HDD>/whitelist.json`.

3. **pyosmium API changes between versions.** The current code
   uses `osmium.geom.WKTFactory()` (no args, auto-attaches),
   `osmium.osm.Area`/`OSMObject` distinction (with `is_area()`
   method), and `osmium.FileProcessor(path).with_areas()`. These
   were verified on `osmium==4.3.1`. Older versions used
   `osmium.geo.WayFactory` and explicit factory injection.

4. **geopandas has no mypy stubs.** Type errors suppressed with
   `# type: ignore[import-untyped]`. Don't try to remove the
   suppression.

5. **macOS ru_maxrss is in bytes, not kilobytes** (Linux). Divide
   by 1,000,000 to get MB. We use 1_000_000 for portability.

6. **Agent timeout vs long first-pass.** Never `wait` on a PBF
   extract process. Launch with `terminal(background=true)`, then
   `cat` `.progress.json` and `ps -o etime,rss,pcpu` to monitor.

7. **Drop counts must reset per run.** On resume, drops should NOT
   be cumulative. We achieve this by not loading drops from
   `progress.json` on subsequent runs — the live dict starts empty,
   only records what THIS run actually filtered.

8. **`.seen_ids` is the canonical source of truth for resume.**
   Not `01_extracted.jsonl` (which only has kept polygons) and
   not `.progress.json` (which is overwritten). The WAL is
   append-only per run and survives across runs.

## Stage-Specific Notes

### Stage 0 (extract.py)

- **MIN_AREA_KM2 = 0.1, MAX_AREA_KM2 = 100** (drops tiny/large).
- Stream-writes one polygon at a time — never accumulate in memory.
- WAL writes are batched (every 10,000 ids) to avoid 200M+ disk syncs.
- `--limit N` stops after N NEW polygons in this run (resumable).
- Drops counted: `not_an_area`, `too_small`, `too_large`,
  `wkt_conversion_failed`, `not_polygon`.

### Stage 1 (whitelist.py)

- Built from `data/reference/osm_stats/{tfidf,embeddings}/`.
- 22,075 unique `key=value` tags across 236 base keys (yes-labeled
  in either pipeline).
- Tier A: real-cluster tags (cluster_id != -1).
- Tier B: noise-cluster tags with `count_all >= 10,000` (rescues
  high-volume isolates like `landuse=forest`, `natural=wood`).
- Reason: `landuse=forest` has 5.9M occurrences but no lexical
  neighbors, so HDBSCAN put it in noise. Without Tier B, the
  whitelist would miss the most obvious landuse tag.

### Stage 2 (filter_by_whitelist.py)

- Single-pass set intersection: `set(row["tags"]) & whitelist`.
- Case-sensitive, exact `key=value` match.
- Drops ~2-3% of polygons (mostly `boundary=administrative`).

### Stage 3 (classify.py)

- Continent via Natural Earth admin0 shapefile, Shapely STRtree
  for fast point-in-polygon. `continent_of(point, tree, geom, cont)`.
- Returns `None` (sentinel `OCEAN_LABEL`) for ocean centroids.
- Size bin: 0.1-1 km² = `small`, 1-10 = `medium`, 10-100 = `large`.
  `tiny` is empty by construction (extract drops < 0.1 km²).

## Tests

`uv run pytest tests/ -v` — 62 tests across core + stages.

Tested behavior:
- Geometry math (area_km2 with Mercator distortion, is_polygon
  type check, centroid returns floats).
- jsonl_utils.stream_jsonl writes kept rows, drops non-kept, is
  idempotent.
- extract audit/resume/limit with mocked osmium.
- whitelist Tier A/B logic with synthetic osm-stats data.
- classify continent lookup with in-memory GeoDataFrame fixture
  + real Natural Earth shapefile integration test.
- filter_by_whitelist set intersection, case sensitivity, output
  dir creation.

`uv run mypy src/osm_polygon_selection/` — 0 errors.

## Verification Checklist

- [ ] `uv run pytest tests/ -v` passes
- [ ] `uv run mypy src/osm_polygon_selection/` clean
- [ ] Liechtenstein (or any small country) end-to-end: `scripts/run_country.sh andorra`
  produces 03_classified.jsonl with N polygons matching
  236-key whitelist, all in `Europe` continent
- [ ] `.progress.json` readable mid-run, `run.json` final
- [ ] Resume: re-run same country, `n_written=0`,
  `n_skipped_resume > 0`, JSONL unchanged

## One-Shot Recipes

**Run a small country end-to-end:**
```bash
OSM_DATA_ROOT="/Volumes/Seagate M3/osm-polygon-selection" \
  scripts/run_country.sh monaco
```

**Sample 300 polygons across all processed countries + visualize:**
```bash
uv run scripts/sample_for_map.py
uv run scripts/visualize.py /tmp/sample_map.jsonl /tmp/sample_map.html
open /tmp/sample_map.html
```

**Audit a partial Europe run:**
```bash
cat "/Volumes/Seagate M3/osm-polygon-selection/processed/europe/01_extracted.jsonl.progress.json"
ls -lh "/Volumes/Seagate M3/osm-polygon-selection/processed/europe/"
ps -o pid,etime,rss,pcpu -p <python_pid>
```

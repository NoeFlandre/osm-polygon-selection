# Dataset State (Europe rollout, June 2026)

This document describes the current state of the OSM polygon dataset
produced by this project as of 27 June 2026. It is intended to be
read alongside `README.md` and the code in `scripts/` and
`src/osm_polygon_selection/stages/`.

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

33 European countries processed end-to-end through Stages 0-3.
12 more countries have PBFs on disk and are partially processed.

### Total classified polygons: 1,067,098

### Per-country breakdown

| Country | Extracted | Whitelisted | Classified | %Pass | Extract status |
|---------|-----------|-------------|------------|-------|----------------|
| albania | 8,646 | 8,423 | 8,423 | 97.4% | killed mid-pipeline |
| andorra | 787 | 776 | 776 | 98.6% | clean |
| austria | 142,280 | 133,711 | 133,711 | 94.0% | clean |
| azores | 3,314 | 2,640 | 2,640 | 79.7% | killed mid-pipeline |
| belarus | 32,845 | 32,828 | 32,828 | 99.9% | killed mid-pipeline |
| belgium | 110,907 | 108,572 | 108,572 | 97.9% | killed mid-pipeline |
| bosnia-herzegovina | 20,345 | 19,252 | 19,252 | 94.6% | killed mid-pipeline |
| bulgaria | 22,336 | 21,405 | 21,405 | 95.8% | killed mid-pipeline |
| croatia | 13,245 | 13,038 | 13,038 | 98.4% | killed mid-pipeline |
| cyprus | 5,782 | 4,846 | 4,846 | 83.8% | clean |
| czech-republic | 290,046 | 269,806 | 269,806 | 93.0% | killed mid-pipeline |
| denmark | 176,511 | 175,795 | 175,795 | 99.6% | clean |
| estonia | 31,365 | 28,134 | 28,134 | 89.7% | killed mid-pipeline |
| faroe-islands | 1,448 | 1,278 | 1,278 | 88.3% | clean |
| guernsey-jersey | 766 | 670 | 670 | 87.5% | clean |
| hungary | 10,621 | 6,715 | 6,715 | 63.2% | killed mid-pipeline |
| iceland | 28,112 | 27,749 | 27,749 | 98.7% | killed mid-pipeline |
| isle-of-man | 2,664 | 2,648 | 2,648 | 99.4% | clean |
| kosovo | 439 | 109 | 109 | 24.8% | killed mid-pipeline |
| latvia | 19,670 | 18,679 | 18,679 | 95.0% | killed mid-pipeline |
| liechtenstein | 585 | 565 | 565 | 96.6% | clean |
| lithuania | 13,475 | 13,363 | 13,363 | 99.2% | killed mid-pipeline |
| luxembourg | 11,664 | 11,460 | 11,460 | 98.3% | clean |
| malta | 697 | 620 | 620 | 89.0% | clean |
| moldova | 15,527 | 15,434 | 15,434 | 99.4% | killed mid-pipeline |
| monaco | 5 | 2 | 2 | 40.0% | clean |
| montenegro | 12,213 | 11,785 | 11,785 | 96.5% | clean |
| portugal | 75,859 | 66,287 | 66,287 | 87.4% | clean |
| romania | 721 | 694 | 694 | 96.3% | killed mid-pipeline |
| serbia | 7,935 | 6,138 | 6,138 | 77.4% | killed mid-pipeline |
| slovakia | 1,978 | 1,887 | 1,887 | 95.4% | killed mid-pipeline |
| slovenia | 646 | 633 | 633 | 98.0% | killed mid-pipeline |
| switzerland | 64,443 | 61,156 | 61,156 | 94.9% | clean |

### Extract status meaning

- **clean**: Stage 0 finished writing the `.run.json` log file
  before the process exited. Every OSM object in the PBF that
  matched the size, area, WKT, and polygon-shape filters was
  yielded and written to `01_extracted.jsonl`. Re-running the
  extract on the same PBF would produce **the same output** (or
  a superset, in the rare case where a polygon was on a relation
  whose member way was not yet indexed when the area was yielded).
- **killed mid-pipeline**: Stage 0 was interrupted (typically by an
  agent session timeout on this codebase's 180-second `wait`
  limit) before reaching the end of the PBF. The yielded polygons
  that made it to `01_extracted.jsonl` are valid and complete; a
  small tail of polygons that would have been yielded later is
  missing. Re-running extract on the same PBF would skip the
  already-seen OSM IDs via the `.seen_ids` WAL and resume yielding
  the remaining ones.

### Countries currently in-progress or pending

- greece: extract started, no classified output yet
- turkey, finland, sweden, ukraine, norway, netherlands, spain,
  poland, italy, united-kingdom, germany, france: PBF downloaded
  but extract not yet started

See `docs/skills/osm-polygon-selection-pipeline/SKILL.md` for
how to resume processing these countries.

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

The orchestrator (`scripts/run_europe.py`) processes all 47 European
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
4. **19 countries were killed mid-pipeline**. Their
   `01_extracted.jsonl` is valid but a small tail of polygons
   (~5-10% estimated) is missing. Re-running extract on the same
   PBF would resume from the WAL and complete them.
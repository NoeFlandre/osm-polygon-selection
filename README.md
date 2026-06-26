# osm-polygon-selection

Select OSM polygons distributed by size and geography for downstream
training/evaluation. Polygons are filtered by an OSM tag whitelist
derived from the [osm-stats](https://github.com/NoeFlandre/osm-stats)
analysis, then stratified by continent + size bin.

## Pipeline

The pipeline is staged. Each stage reads from the previous stage's
output and writes to the next:

```
Stage 0  scripts/stage0_extract.py        PBF          -> JSONL (polygons)
Stage 1  scripts/stage1_build_whitelist.py osm-stats    -> whitelist.json
Stage 2  scripts/stage2_filter.py         JSONL + WL   -> filtered JSONL
Stage 3  scripts/stage3_classify.py       JSONL + shp  -> classified JSONL
                                                  (continent + size_bin)
```

Visualize any stage's output:

```
scripts/visualize.py data/processed/lichchtenstein/03_classified.jsonl out.html
```

## Layout

```
src/osm_polygon_selection/    library modules
  geometry_utils.py           CRS / area / centroid helpers
  extract.py                  PBF streaming (osmium)
  whitelist.py                OSM tag whitelist from osm-stats
  filter_by_whitelist.py      tag-intersection filter
  classify.py                 continent (Natural Earth) + size bin

scripts/                      CLI entry points (one per stage)
  stage0_extract.py
  stage1_build_whitelist.py
  stage2_filter.py
  stage3_classify.py
  visualize.py                render JSONL to interactive HTML map

tests/                        pytest suite (40 tests)

data/
  raw/                        downloaded PBFs (gitignored)
  reference/                  static reference data (versioned)
    natural_earth/            admin0 shapefile
    osm_stats/                tag analysis CSVs + XLSX
  processed/                  pipeline outputs (one subdir per region)
  whitelist.json              global whitelist (built by stage 1)

docs/
  whitelist_decisions.md      rationale for whitelist filtering
```

## Quickstart

```bash
# Install deps
uv sync

# Stage 0: extract polygons from a PBF (Liechtenstein example)
curl -L -o data/raw/liechtenstein-latest.osm.pbf \
  https://download.geofabrik.de/europe/liechtenstein-latest.osm.pbf
uv run scripts/stage0_extract.py \
  data/raw/liechtenstein-latest.osm.pbf \
  data/processed/lichchtenstein/01_extracted.jsonl

# Stage 1: build the whitelist (once)
uv run scripts/stage1_build_whitelist.py data/reference/osm_stats data/whitelist.json

# Stage 2: filter by whitelist
uv run scripts/stage2_filter.py \
  data/processed/lichchtenstein/01_extracted.jsonl \
  data/whitelist.json \
  data/processed/lichchtenstein/02_filtered.jsonl

# Stage 3: classify (continent + size bin)
uv run scripts/stage3_classify.py \
  data/processed/lichchtenstein/02_filtered.jsonl \
  data/reference/natural_earth/ne_110m_admin_0_countries.shp \
  data/processed/lichchtenstein/03_classified.jsonl

# Visualize
uv run scripts/visualize.py \
  data/processed/lichchtenstein/03_classified.jsonl \
  data/processed/lichchtenstein/03_classified_map.html
```

## Tests

```bash
uv run pytest tests/ -v
uv run mypy src/osm_polygon_selection/
```

## Data attribution

- OSM data: (c) OpenStreetMap contributors, ODbL
- Natural Earth: public domain, naturalearthdata.com
- osm-stats analysis: github.com/NoeFlandre/osm-stats (MIT code)

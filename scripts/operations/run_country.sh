#!/bin/bash
# Run the full pipeline on one country.
# Usage: ./scripts/operations/run_country.sh <geofabrik_name> [stage0_limit]
# Example: ./scripts/operations/run_country.sh andorra
#          ./scripts/operations/run_country.sh belgium 5000
#
# Env vars (maintainer-only):
#   OSM_DATA_ROOT  - the maintainer HDD root (default:
#                    sibling-of-repo osm-polygon-selection, or whatever
#                    RuntimeConfig.from_env() returns).

set -e

COUNTRY="$1"
LIMIT="${2:-}"  # empty = no limit (run to completion)
HDD="${OSM_DATA_ROOT:-/Volumes/Seagate M3/osm-polygon-selection}"
RAW="$HDD/raw"
PROC="$HDD/processed/$COUNTRY"
PBF="$RAW/${COUNTRY}-latest.osm.pbf"

mkdir -p "$RAW" "$PROC"

# Download if missing.
if [ ! -f "$PBF" ]; then
    echo "[$COUNTRY] downloading PBF..."
    curl -L --silent --show-error -o "$PBF" \
        "https://download.geofabrik.de/europe/${COUNTRY}-latest.osm.pbf"
    echo "[$COUNTRY] downloaded $(du -h "$PBF" | cut -f1)"
fi

# Whitelist (copy if missing on HDD).
if [ ! -f "$HDD/whitelist.json" ]; then
    echo "[$COUNTRY] copying whitelist to HDD"
    cp data/whitelist.json "$HDD/whitelist.json"
fi

# Stage 0: extract.
LIMIT_ARG=""
if [ -n "$LIMIT" ]; then
    LIMIT_ARG="--limit $LIMIT"
fi
echo "[$COUNTRY] stage 0: extract $LIMIT_ARG"
OSM_DATA_ROOT="$HDD" \
    uv run scripts/stage0_extract.py "$PBF" "$PROC/01_extracted.jsonl" $LIMIT_ARG

# Stage 2: filter.
echo "[$COUNTRY] stage 2: filter"
OSM_DATA_ROOT="$HDD" \
    uv run scripts/stage2_filter.py \
        "$PROC/01_extracted.jsonl" \
        "$HDD/whitelist.json" \
        "$PROC/02_filtered.jsonl"

# Stage 3: classify.
echo "[$COUNTRY] stage 3: classify"
OSM_DATA_ROOT="$HDD" \
    uv run scripts/stage3_classify.py \
        "$PROC/02_filtered.jsonl" \
        data/reference/natural_earth/ne_110m_admin_0_countries.shp \
        "$PROC/03_classified.jsonl"

echo "[$COUNTRY] DONE. Polygons: $(wc -l < "$PROC/03_classified.jsonl")"

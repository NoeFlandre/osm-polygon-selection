#!/bin/bash
# Complete stages 2+3 for any country that has 01_extracted.jsonl
# but no 03_classified.jsonl yet.
# Usage: ./scripts/complete_pipeline.sh <country>

set -e

COUNTRY="$1"
HDD="/Volumes/Seagate M3/osm-polygon-selection"
PROC="$HDD/processed/$COUNTRY"
SRC="$PROC/01_extracted.jsonl"
FILT="$PROC/02_filtered.jsonl"
CLS="$PROC/03_classified.jsonl"

if [ -z "$COUNTRY" ]; then
    echo "usage: $0 <country>"
    exit 1
fi

if [ -f "$CLS" ]; then
    n=$(wc -l < "$CLS")
    echo "$COUNTRY: already done ($n)"
    exit 0
fi

if [ ! -f "$SRC" ]; then
    echo "$COUNTRY: no extract yet, run scripts/run_country.sh $COUNTRY first"
    exit 1
fi

n_src=$(wc -l < "$SRC")
echo "$COUNTRY: $n_src polygons extracted, running filter+classify..."

OSM_DATA_ROOT="$HDD" \
    uv run scripts/stage2_filter.py "$SRC" "$HDD/whitelist.json" "$FILT" > /dev/null

OSM_DATA_ROOT="$HDD" \
    uv run scripts/stage3_classify.py "$FILT" \
        data/reference/natural_earth/ne_110m_admin_0_countries.shp \
        "$CLS" > /dev/null

n_cls=$(wc -l < "$CLS")
echo "$COUNTRY: $n_cls classified"

# Whitelist decisions

The OSM tag whitelist filters polygons to those tagged with at least one
"landuse/landcover-relevant" key=value pair. Source: the manual labeling
from the osm-stats project (blog post "OSM data analysis for landuse",
10 Jun 2026).

## Inputs

Copied from `osm-stats/output/standardize_first/` into
`data/osm_stats/`. Two parallel pipelines (TF-IDF and embeddings,
both retained for complementarity), each with:

- `base_key_families.xlsx`: one row per supercluster with the `keep` label
  (yes / uncertain / no) and `sc_is_polygon_friendly` flag.
- `cluster_memberships*.csv`: one row per (cluster_id, base_key, key,
  value) with `count_all` and a `feature` column (key|value form).

## Filter policy

1. `keep == "yes"` in either pipeline (union across TF-IDF and
   embeddings). Drops `uncertain` and `no`. After this step the union
   of base keys is 236.
2. **Two-tier tag inclusion for each kept base key:**
   - **Tier A (real clusters):** all tags from `cluster_id != -1` in
     `cluster_memberships*.csv`. Always included.
   - **Tier B (noise rescue):** tags with `cluster_id == -1` (HDBSCAN
     noise) are included if their `count_all >= NOISE_RESCUE_THRESHOLD`
     (default: 10,000). These are high-volume tags that HDBSCAN failed
     to cluster — typically isolated strings like `landuse=forest`
     (5.9M occurrences) or `natural=wood` (12.4M occurrences) which
     have no near-duplicate in the corpus but are clearly
     landuse-relevant.
3. Format: `"key=value"` strings (matching the format used in our
   polygon's `tags` field, so intersection is trivial).
4. Dedup via Python `set`. A given tag may appear in both pipelines and
   across multiple clusters within a pipeline.

## What we explicitly do NOT do

- **No `count_all` threshold on Tier A.** The osm-stats pipeline
  already filtered to `count_all >= 500` upstream; further thinning
  would drop legitimate per-value tags.
- **No `sc_is_polygon_friendly` filter.** Our polygon extraction
  already drops node-only and line-only geometries. A base key flagged
  point-heavy in osm-stats will produce zero surviving polygons for
  point-only tags (e.g. `natural=tree`) once we run extraction on a
  planet PBF, so the whitelist need not preempt that.
- **No re-clustering.** The osm-stats `cluster_memberships*.csv` files
  are taken as-is. HDBSCAN is non-deterministic, but the labeled output
  is what we trust.

## Output

`data/whitelist.json`: a JSON-encoded list of unique `"key=value"`
strings. Loaded by downstream stages as a Python `set[str]`.

## Source attribution

Pipeline: github.com/NoeFlandre/osm-stats. Methodology and manual
labels: noeflandre.com/posts/osm-data-analysis (10 Jun 2026, MIT code,
CC BY content).

# Whitelist decisions

The OSM tag whitelist filters polygons to those tagged with at
least one `key=value` pair describing physical land-use /
land-cover (`natural=wood`, `landuse=forest`, `leisure=park`,
…). Source: the manual labeling from the osm-stats project
(blog post [OSM data analysis for landuse](https://noeflandre.com/posts/osm-data-analysis),
10 Jun 2026).

## The two pipelines

Copied from `osm-stats/output/standardize_first/` into
`data/osm_stats/`. **Both pipelines are retained and unioned**
because each catches different patterns:

| Pipeline       | File                                        | What it clusters by                       | Strengths                                                          | Weaknesses                              |
|----------------|---------------------------------------------|-------------------------------------------|--------------------------------------------------------------------|-----------------------------------------|
| **TF-IDF**     | `tfidf/cluster_memberships.csv`             | Lexical similarity of key/value strings   | Canonical high-volume forms (`landuse=residential`, `natural=water`) | Misses semantic synonyms                |
| **Embeddings** | `embeddings/cluster_memberships_embeddings.csv` | Semantic similarity of learned embeddings  | Non-lexical patterns (`landuse=farmyard` ≈ `landuse=meadow` ≈ `landuse=farmland`) | Noisier; sparser per-cluster signal     |

Each pipeline independently produces a `keep=yes | uncertain | no`
label per base key (e.g. `landuse`, `natural`, `leisure`,
`amenity`, `highway`, `building`, …) in its `base_key_families.xlsx`,
plus per-tag rows in `cluster_memberships*.csv` with
`(cluster_id, base_key, key, value, count_all, feature)`.

## Filter policy

1. **`keep == "yes"` in either pipeline → base key survives.**
   Drops `uncertain` and `no` in both pipelines. After this
   step the union is **236 base keys**.
2. **Two-tier tag inclusion per kept base key:**
   - **Tier A (real clusters):** every tag from
     `cluster_id != -1` in `cluster_memberships*.csv`.
   - **Tier B (noise rescue):** tags with `cluster_id == -1`
     (HDBSCAN noise) included if `count_all >= 10,000`.
     These are high-volume tags with no near-duplicate in the
     corpus but clearly landuse-relevant, e.g.
     `landuse=forest` (~5.9M), `natural=wood` (~12.4M).
3. Format: `"key=value"` strings (matches the format used in our
   polygon's `tags` field, so intersection is trivial).
4. Dedup via Python `set`. A given tag may appear in both
   pipelines and across multiple clusters within a pipeline.

After dedup the union contains **22,075 unique `key=value`
strings**.

## What we explicitly do NOT do

- **No `count_all` threshold on Tier A.** The osm-stats pipeline
  already filtered to `count_all >= 500` upstream; further
  thinning would drop legitimate per-value tags.
- **No `sc_is_polygon_friendly` filter.** Our polygon extraction
  already drops node-only and line-only geometries. A base key
  flagged point-heavy in osm-stats will produce zero surviving
  polygons for point-only tags (e.g. `natural=tree`) once we
  run extraction on a planet PBF, so the whitelist need not
  preempt that.
- **No re-clustering.** The osm-stats `cluster_memberships*.csv`
  files are taken as-is. HDBSCAN is non-deterministic, but the
  labeled output is what we trust.

## Output

`data/whitelist.json`: a JSON-encoded list of unique `"key=value"`
strings. Loaded by downstream stages as a Python `set[str]`.

## Source attribution

Pipeline: github.com/NoeFlandre/osm-stats. Methodology and manual
labels: noeflandre.com/posts/osm-data-analysis (10 Jun 2026, MIT code,
CC BY content).

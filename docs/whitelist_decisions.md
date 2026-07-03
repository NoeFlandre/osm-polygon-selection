# Whitelist decisions

The OSM tag whitelist filters polygons to those tagged with at
least one `key=value` pair describing physical land-use /
land-cover (`natural=wood`, `landuse=forest`, `leisure=park`,
…). Source: the manual labeling from the osm-stats project
(blog post [OSM data analysis for landuse](https://noeflandre.com/posts/osm-data-analysis),
10 Jun 2026).

## The two pipelines

Copied from `osm-stats/output/standardize_first/` into
`data/reference/osm_stats/`. **Both pipelines are retained and
unioned** because each catches different patterns:

| Pipeline       | File                                        | What it clusters by                       | Strengths                                                          | Weaknesses                              |
|----------------|---------------------------------------------|-------------------------------------------|--------------------------------------------------------------------|-----------------------------------------|
| **TF-IDF**     | `tfidf/cluster_memberships.csv`             | Lexical similarity of key/value strings (tokenized word pieces → sparse TF-IDF vectors → cosine distance → HDBSCAN) | Canonical high-volume forms (`landuse=residential`, `natural=water`); robust to spelling variants when shared token is dominant | Cannot connect tags with no shared surface tokens (`landuse=farmyard`, `landuse=meadow`, `landuse=farmland` end up in different clusters) |
| **Embeddings** | `embeddings/cluster_memberships_embeddings.csv` | Semantic similarity of learned embeddings (`all-MiniLM-L6-v2` → 384-dim L2-normalized → cosine distance → HDBSCAN) | Non-lexical patterns (`landuse=farmyard` ≈ `landuse=meadow` ≈ `landuse=farmland` cluster together) | Rarer tags drift toward the nearest cluster centroid → potential false positives (handled by manual labels downstream) |

Pipeline sizes:

| Pipeline  | `cluster_memberships*.csv` rows | base keys covered | HDBSCAN clusters |
|-----------|--------------------------------:|------------------:|-----------------:|
| TF-IDF    |                         225,684 |             1,829 |            8,833 |
| Embeddings|                         225,684 |             1,829 |            4,955 |

Both pipelines produce a `base_key_families.xlsx` (one row per
base key, with manual `keep=yes | uncertain | no` label) and a
`cluster_memberships*.csv` (one row per `(cluster_id,
base_key, key, value)` with `count_all` and a `feature`
column).

## Filter policy

1. **`keep == "yes"` in either pipeline → base key survives.**
   Drops `uncertain` and `no` in both pipelines. After this
   step the union is **236 base keys** (90 in both pipelines,
   67 TF-IDF-only, 79 embeddings-only).

   | Pipeline  | base keys | yes | uncertain | no |
   |-----------|----------:|----:|----------:|---:|
   | TF-IDF    |       427 | 157 |        54 | 216 |
   | Embeddings|       433 | 169 |        57 | 207 |
   | **Union** |   **464** |**236** | — | — |

2. **Two-tier tag inclusion per kept base key:**
   - **Tier A (real clusters):** every tag from
     `cluster_id != -1` in `cluster_memberships*.csv` for the
     kept base keys. Always included.
     - TF-IDF: **16,685 tags**.
     - Embeddings: **18,382 tags**.
   - **Tier B (noise rescue):** tags with `cluster_id == -1`
     (HDBSCAN noise) included if `count_all >= 10,000`.
     These are high-volume tags with no near-duplicate in the
     corpus but clearly landuse-relevant, e.g.
     `landuse=forest` (~5.9 M occurrences) and `natural=wood`
     (~12.4 M occurrences).
     - TF-IDF: **1,171 tags**.
     - Embeddings: **1,023 tags**.

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

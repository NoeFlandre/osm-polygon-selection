"""Load the OSM tag whitelist from osm-stats outputs.

The whitelist is the set of "key=value" tags whose base key was manually
labeled "yes" in either the TF-IDF or embeddings pipeline of osm-stats
(see docs/whitelist_decisions.md).

Source files (copied into data/osm_stats/):
  tfidf/base_key_families.xlsx         + tfidf/cluster_memberships.csv
  embeddings/base_key_families.xlsx    + embeddings/cluster_memberships_embeddings.csv

Pipeline:
  1. Read both base_key_families.xlsx; filter keep=yes; union base keys.
  2. Read both cluster_memberships*.csv; drop cluster_id == -1 (noise);
     keep rows whose base_key is in our union; build "key=value" strings.
  3. Return the set.
"""

import json
from pathlib import Path

import pandas as pd

# Subdirectory layout under the osm-stats root.
TFIDF_DIR = "tfidf"
EMBEDDINGS_DIR = "embeddings"

# File names per pipeline.
FAMILIES_FILE = "base_key_families.xlsx"
MEMBERSHIPS_FILE = "cluster_memberships.csv"
MEMBERSHIPS_FILE_EMB = "cluster_memberships_embeddings.csv"

# Label values we keep (from the manual labeling).
KEEP_LABEL = "yes"

# Noise cluster id produced by HDBSCAN in osm-stats.
NOISE_CLUSTER_ID = -1

# Minimum count_all to rescue a tag from the noise bucket.
# HDBSCAN marks isolated tags (no near-duplicates) as noise. Some are
# legitimately high-volume (e.g. landuse=forest has ~5.9M occurrences
# but no lexical neighbors). The threshold admits only clearly
# significant noise tags; typos and rare variants stay excluded.
NOISE_RESCUE_THRESHOLD = 10_000


def _load_kept_base_keys(osm_stats_root: Path) -> set[str]:
    """Union of base_keys labeled 'yes' in either pipeline."""
    kept: set[str] = set()
    for subdir, families_name in [
        (TFIDF_DIR, FAMILIES_FILE),
        (EMBEDDINGS_DIR, FAMILIES_FILE),
    ]:
        path = osm_stats_root / subdir / families_name
        df = pd.read_excel(path)
        if df.empty or "keep" not in df.columns:
            continue
        kept.update(df.loc[df["keep"] == KEEP_LABEL, "base_key"].tolist())
    return kept


def _load_tag_strings(
    osm_stats_root: Path, subdir: str, memberships_name: str,
    kept_base_keys: set[str],
) -> set[str]:
    """Read one pipeline's cluster_memberships, filter, format as key=value.

    Tier A: real-cluster tags (cluster_id != -1) for any kept base key.
    Tier B: noise-cluster tags (cluster_id == -1) for kept base keys
            when count_all >= NOISE_RESCUE_THRESHOLD.
    """
    path = osm_stats_root / subdir / memberships_name
    df = pd.read_csv(path)
    if df.empty or "base_key" not in df.columns:
        return set()
    df = df[df["base_key"].isin(kept_base_keys)] if kept_base_keys else df.iloc[0:0]
    if df.empty:
        return set()
    tier_a = df[df["cluster_id"] != NOISE_CLUSTER_ID]
    tier_b = df[
        (df["cluster_id"] == NOISE_CLUSTER_ID)
        & (df["count_all"] >= NOISE_RESCUE_THRESHOLD)
    ]
    combined = pd.concat([tier_a, tier_b], ignore_index=True)
    if combined.empty:
        return set()
    return {f"{k}={v}" for k, v in zip(combined["key"], combined["value"])}


def load_whitelist(
    osm_stats_root: Path,
    out_path: Path | None = None,
) -> set[str]:
    """Build the union whitelist from both pipelines.

    Args:
        osm_stats_root: directory containing tfidf/ and embeddings/ subdirs.
        out_path: if given, write the whitelist as JSON to this file.

    Returns:
        A set of "key=value" tag strings (deduplicated).
    """
    kept_base_keys = _load_kept_base_keys(osm_stats_root)
    tags = _load_tag_strings(
        osm_stats_root, TFIDF_DIR, MEMBERSHIPS_FILE, kept_base_keys,
    )
    tags |= _load_tag_strings(
        osm_stats_root, EMBEDDINGS_DIR, MEMBERSHIPS_FILE_EMB, kept_base_keys,
    )
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(sorted(tags)))
    return tags

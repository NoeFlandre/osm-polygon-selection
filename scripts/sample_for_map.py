"""Sample polygons across all processed countries for a lightweight map.

Strategy:
- Stratified sampling: each country contributes proportionally to its
  share of total polygons, with a small floor (so small countries are
  visible) and a cap (so big countries don't dominate).
- Within each country, sample by size_bin (tiny/small/medium/large)
  to show size distribution.
- Color-code by country for visual distinction.
- Output is a single JSONL with the same schema as 03_classified.jsonl
  so the existing visualize.py works on it directly.
"""

import json
import os
import random
from pathlib import Path

import pyarrow.parquet as pq

PROCESSED_ROOT = Path("/Volumes/Seagate M3/osm-polygon-selection/processed")
DATASET_ROOT = Path("/Users/noeflandre/osm-polygon-selection/data/dataset")
OUT_PATH = Path("/tmp/sample_map.jsonl")

# Per-country floor and cap. Floor ensures small countries show up;
# cap prevents one country from dominating the map.
FLOOR = 15          # every country gets at least this many
CAP_RATIO = 0.40    # no country gets more than 40% of the sample
TARGET_TOTAL = 1200  # dense coverage, ~5MB HTML

# Per-bin allocation within a country. Sum should be ~1.0; we just
# sample up to this many per bin.
BIN_BUDGET = {
    "tiny": 4,
    "small": 12,
    "medium": 8,
    "large": 4,
}

random.seed(42)


def country_share(country_counts: dict[str, int], total: int) -> dict[str, int]:
    """Allocate TARGET_TOTAL polygons across countries.

    Each country gets at least FLOOR, at most CAP_RATIO * TARGET_TOTAL.
    Remainder is distributed proportionally to the country's share
    of the total polygon pool.
    """
    cap = int(CAP_RATIO * TARGET_TOTAL)
    raw = {
        c: max(FLOOR, int(TARGET_TOTAL * count / total))
        for c, count in country_counts.items()
    }
    # Cap oversize countries
    raw = {c: min(n, cap) for c, n in raw.items()}

    # Distribute the difference between sum(raw) and TARGET_TOTAL
    diff = TARGET_TOTAL - sum(raw.values())
    if diff > 0:
        # Give the extra to the largest country (it has the most to choose from)
        biggest = max(country_counts, key=lambda c: country_counts[c])
        raw[biggest] += diff
    return raw


def load_from_parquet(country: str, n_needed: int) -> list[dict]:
    """Load at most n_needed polygons for a country from its parquet file.

    Parquet is much faster to read than JSONL when we only need a
    subset (which is the case here). For a 12 MB parquet with
    ~270k rows, we can read a 1200-row random subset in <100 ms.
    """
    pq_file = DATASET_ROOT / f"{country}.parquet"
    if not pq_file.exists():
        return []
    # Read with row-group filtering if available; otherwise load full
    # table and sample.
    table = pq.read_table(pq_file, columns=[
        "osm_id", "centroid_lon", "centroid_lat", "area_km2",
        "continent", "size_bin", "country",
    ])
    if table.num_rows == 0:
        return []
    if table.num_rows <= n_needed:
        df = table.to_pylist()
    else:
        # Random row indices
        rng = random.Random(42)
        idx = rng.sample(range(table.num_rows), n_needed)
        df = table.take(idx).to_pylist()
    return df


def load_from_parquet_by_bin(country: str, n_per_bin: dict[str, int]) -> dict[str, list[dict]]:
    """Like load_from_parquet but groups by size_bin.

    n_per_bin maps size_bin -> max rows to sample from that bin.
    """
    pq_file = DATASET_ROOT / f"{country}.parquet"
    if not pq_file.exists():
        return {b: [] for b in BIN_BUDGET}
    table = pq.read_table(pq_file, columns=[
        "osm_id", "centroid_lon", "centroid_lat", "area_km2",
        "continent", "size_bin", "country",
    ])
    if table.num_rows == 0:
        return {b: [] for b in BIN_BUDGET}
    df = table.to_pandas()
    by_bin: dict[str, list[dict]] = {b: [] for b in BIN_BUDGET}
    for _, row in df.iterrows():
        rec = row.to_dict()
        by_bin.setdefault(rec.get("size_bin", "small"), []).append(rec)
    # Cap each bin to n_per_bin[b]
    rng = random.Random(42)
    for b in by_bin:
        cap = n_per_bin.get(b, BIN_BUDGET[b])
        if len(by_bin[b]) > cap:
            by_bin[b] = rng.sample(by_bin[b], cap)
    return by_bin


def main() -> None:
    # 1. Count countries by reading manifest (no row-level reads yet).
    manifest = DATASET_ROOT / "manifest.json"
    if manifest.exists():
        m = json.loads(manifest.read_text())
        countries_done = m["countries"]
        counts = {c["country"]: c["n_polygons"] for c in countries_done}
    else:
        # Fallback: scan JSONL files (slower)
        countries_done = []
        counts = {}
        for country_dir in sorted(PROCESSED_ROOT.iterdir()):
            if not country_dir.is_dir():
                continue
            classified = country_dir / "03_classified.jsonl"
            if not classified.exists():
                continue
            n = sum(1 for _ in classified.open())
            counts[country_dir.name] = n

    if not counts:
        print("no classified countries found")
        return

    total = sum(counts.values())
    print(f"found {len(counts)} countries, {total} classified polygons total")

    # 2. Allocate per-country sample size.
    allocation = country_share(counts, total)
    print("per-country allocation:", allocation)

    # 3. For each country, sample by size_bin from parquet.
    sampled: list[dict] = []
    for country, target in allocation.items():
        n_per_bin = {b: min(BIN_BUDGET[b], target) for b in BIN_BUDGET}
        by_bin = load_from_parquet_by_bin(country, n_per_bin)
        per_country = []
        bins = list(BIN_BUDGET.keys())
        idx = 0
        while len(per_country) < target:
            b = bins[idx % len(bins)]
            pool = by_bin.get(b, [])
            if pool:
                picked = pool.pop()
                picked["country"] = country  # tag for visualization
                # Drop unneeded fields (keep light for the HTML map)
                picked.pop("tags", None)
                per_country.append(picked)
            idx += 1
            if idx > 10 * target and not pool:
                break
        sampled.extend(per_country)
        print(f"  {country}: took {len(per_country)} of {target} (pool {counts[country]})")

    # 4. Write the sample.
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w") as f:
        for row in sampled:
            f.write(json.dumps(row) + "\n")
    print(f"\nwrote {len(sampled)} polygons to {OUT_PATH}")


if __name__ == "__main__":
    main()

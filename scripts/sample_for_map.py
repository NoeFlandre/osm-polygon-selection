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
import random
from collections import Counter
from pathlib import Path

PROCESSED_ROOT = Path("/Volumes/Seagate M3/osm-polygon-selection/processed")
OUT_PATH = Path("/tmp/sample_map.jsonl")

# Per-country floor and cap. Floor ensures small countries show up;
# cap prevents one country from dominating the map.
FLOOR = 15          # every country gets at least this many
CAP_RATIO = 0.40    # no country gets more than 40% of the sample
TARGET_TOTAL = 1000  # dense coverage, ~5MB HTML

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


def main() -> None:
    # 1. Collect all classified polygons, grouped by country.
    countries: dict[str, list[dict]] = {}
    for country_dir in sorted(PROCESSED_ROOT.iterdir()):
        if not country_dir.is_dir():
            continue
        classified = country_dir / "03_classified.jsonl"
        if not classified.exists():
            continue
        rows = []
        with classified.open() as f:
            for line in f:
                rows.append(json.loads(line))
        countries[country_dir.name] = rows

    if not countries:
        print("no classified JSONL files found")
        return

    total = sum(len(v) for v in countries.values())
    print(f"found {len(countries)} countries, {total} classified polygons total")

    # 2. Allocate per-country sample size.
    counts = {c: len(v) for c, v in countries.items()}
    allocation = country_share(counts, total)
    print("per-country allocation:", allocation)

    # 3. For each country, sample by size_bin.
    sampled: list[dict] = []
    for country, rows in countries.items():
        target = allocation[country]
        by_bin: dict[str, list[dict]] = {b: [] for b in BIN_BUDGET}
        for row in rows:
            by_bin.setdefault(row.get("size_bin", "small"), []).append(row)
        per_country = []
        # Round-robin across bins: take budget from each bin until
        # we've hit the target or run out.
        bins = list(BIN_BUDGET.keys())
        idx = 0
        while len(per_country) < target:
            b = bins[idx % len(bins)]
            pool = by_bin.get(b, [])
            if pool:
                picked = pool.pop(random.randrange(len(pool)))
                picked["country"] = country  # tag for visualization
                # Drop the WKT geometry: the visualize script re-derives
                # the shape from centroid + area for display. Keeps the
                # sample JSONL tiny and the rendered map fast.
                if "geometry" in picked:
                    del picked["geometry"]
                per_country.append(picked)
            idx += 1
            if idx > 10 * target and not pool:
                break  # nothing left to take
        sampled.extend(per_country)
        print(f"  {country}: took {len(per_country)} of {target} (pool {len(rows)})")

    # 4. Write the sample.
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w") as f:
        for row in sampled:
            f.write(json.dumps(row) + "\n")
    print(f"\nwrote {len(sampled)} polygons to {OUT_PATH}")


if __name__ == "__main__":
    main()

"""Sample polygons across all processed countries for a lightweight map.

Strategy (improved for "highly representative" maps):

1. **Power-law per-country allocation**: each country gets
   ``clamp(round(n_polygons ** POWER), FLOOR, CAP)`` polygons. This
   compresses the per-country range so dense countries (germany: 1.1M)
   don't crowd out sparse ones (monaco: 2), while still preserving
   the relative density differences. With ``POWER=0.4``:
   - monaco (2 polygons) -> floor 8 (only 2 exist; shown in full)
   - germany (1,131,888 polygons) -> ~179
   The raw germany/monaco ratio is ~565,000x; the sampled ratio is ~22x.

2. **Spatial coverage within each country**: bucket each polygon's
   centroid into a ``K x K`` grid where ``K = ceil(sqrt(target_n))``,
   then pick one random polygon per cell using reservoir sampling.
   This avoids clustering in dense regions (e.g. cities) and ensures
   the sampled polygons are well-spread across the country's bounding
   box. If the country has fewer than ``target_n`` non-empty cells
   (very sparse or linear-shaped), top up with a uniform random sample.

3. **Floor (FLOOR=8)** so even monaco's 2 polygons are visible.
4. **Cap (CAP=200)** so germany doesn't fill the map.

Output is a JSONL with the same schema as the parquet files so the
existing ``visualize.py`` works on it directly.
"""

import json
import math
import os
import random
from pathlib import Path

import pyarrow.parquet as pq

PROCESSED_ROOT = Path("/Volumes/Seagate M3/osm-polygon-selection/processed")
DATASET_ROOT = Path(os.environ.get(
    "OSM_DATASET_DIR",
    str(Path(__file__).resolve().parent.parent / "data" / "dataset"),
))
OUT_PATH = Path("/tmp/sample_map.jsonl")

# Per-country floor and cap. Floor ensures small countries show up;
# cap prevents one country from dominating the map.
FLOOR = 8          # every country gets at least this many
CAP = 200          # never more than this per country
POWER = 0.4        # power-law compression exponent

# Parquet columns we read. Mirrors what visualize.py reads.
GEO_COLS = ["centroid_lon", "centroid_lat"]
ALL_COLS = GEO_COLS + [
    "osm_id", "area_km2", "continent",
    "size_bin", "matched_tag", "country",
]

random.seed(42)


def power_law_alloc(country_counts: dict[str, int]) -> dict[str, int]:
    """Allocate target sample size per country using power-law compression.

    ``n_target = clamp(round(n_polygons ** POWER), FLOOR, CAP)``
    """
    return {
        c: max(FLOOR, min(CAP, round(count ** POWER)))
        for c, count in country_counts.items()
    }


def compute_bbox(pq_file: Path) -> tuple[float, float, float, float] | None:
    """Stream row groups and find centroid bbox.

    Returns (min_lon, max_lon, min_lat, max_lat), or None if empty.
    """
    pf = pq.ParquetFile(pq_file)
    min_lon = min_lat = float("inf")
    max_lon = max_lat = float("-inf")
    n_rows = 0
    for rg in range(pf.num_row_groups):
        t = pf.read_row_group(rg, columns=GEO_COLS)
        lons = t["centroid_lon"].to_pylist()
        lats = t["centroid_lat"].to_pylist()
        for lon, lat in zip(lons, lats):
            if lon is None or lat is None:
                continue
            if lon < min_lon:
                min_lon = lon
            if lon > max_lon:
                max_lon = lon
            if lat < min_lat:
                min_lat = lat
            if lat > max_lat:
                max_lat = lat
            n_rows += 1
    if n_rows == 0:
        return None
    return min_lon, max_lon, min_lat, max_lat


def grid_sample_country(
    pq_file: Path,
    target_n: int,
    rng: random.Random,
) -> list[dict]:
    """Sample ``target_n`` polygons spread geographically across the country.

    Algorithm:
    1. Compute centroid bbox from a streaming pass over row groups.
    2. Pick ``K = max(1, ceil(sqrt(target_n)))`` so K*K cells can hold
       at least ``target_n`` samples (one per cell).
    3. Second streaming pass: bucket each polygon into its cell using
       reservoir sampling of size 1 (keep a uniformly random member
       of each cell). Memory cost is O(K^2) records.
    4. If we got fewer than ``target_n`` non-empty cells, top up with
       a uniform random sample of additional rows.
    5. Cap output at ``target_n``.
    """
    bbox = compute_bbox(pq_file)
    if bbox is None:
        return []
    min_lon, max_lon, min_lat, max_lat = bbox

    K = max(1, math.ceil(math.sqrt(target_n)))
    lon_step = (max_lon - min_lon) / K if max_lon > min_lon else 1e-9
    lat_step = (max_lat - min_lat) / K if max_lat > min_lat else 1e-9

    # cell_record: one representative record (dict) per cell.
    # cell_count: how many records seen for this cell (for reservoir).
    cell_record: dict[tuple[int, int], dict] = {}
    cell_count: dict[tuple[int, int], int] = {}

    pf = pq.ParquetFile(pq_file)
    for rg in range(pf.num_row_groups):
        t = pf.read_row_group(rg, columns=ALL_COLS)
        rows = t.to_pylist()
        for rec in rows:
            lon = rec.get("centroid_lon")
            lat = rec.get("centroid_lat")
            if lon is None or lat is None:
                continue
            ix = min(K - 1, max(0, int((lon - min_lon) / lon_step)))
            iy = min(K - 1, max(0, int((lat - min_lat) / lat_step)))
            cell = (ix, iy)
            n_seen = cell_count.get(cell, 0) + 1
            cell_count[cell] = n_seen
            if cell not in cell_record or rng.random() < 1 / n_seen:
                cell_record[cell] = rec

    # Deterministic ordering: by grid index (south-to-north, west-to-east).
    sampled = [cell_record[c] for c in sorted(cell_record.keys())]

    # Top up if grid sample came up short (very sparse / linear countries).
    if len(sampled) < target_n:
        needed = target_n - len(sampled)
        # Read only the columns we need and take a random subset.
        # For very small countries (e.g. monaco), the whole file may
        # already be in sampled; just emit whatever's left.
        all_t = pq.read_table(pq_file, columns=ALL_COLS)
        n_total = all_t.num_rows
        if n_total <= needed:
            extra = all_t.to_pylist()
        else:
            idx = rng.sample(range(n_total), needed)
            extra = all_t.take(idx).to_pylist()
        sampled.extend(extra)

    return sampled[:target_n]


def main() -> None:
    # 1. Read the manifest to get per-country polygon counts.
    manifest = DATASET_ROOT / "manifest.json"
    if manifest.exists():
        m = json.loads(manifest.read_text())
        countries_done = m["countries"]
        counts = {c["country"]: c["n_polygons"] for c in countries_done}
    else:
        # Fallback: count rows in each 03_classified.jsonl.
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

    # Drop countries with zero polygons (no point trying to sample).
    counts = {c: n for c, n in counts.items() if n > 0}

    if not counts:
        print("no classified countries found")
        return

    total = sum(counts.values())
    print(f"found {len(counts)} countries, {total:,} classified polygons total")

    # 2. Allocate per-country sample size.
    allocation = power_law_alloc(counts)
    total_target = sum(allocation.values())
    print(f"per-country allocation sums to {total_target} samples "
          f"(floor={FLOOR}, cap={CAP}, power={POWER})")

    # 3. Per country, do a grid-stratified sample.
    rng = random.Random(42)
    sampled: list[dict] = []
    for country, target in sorted(allocation.items()):
        pq_file = DATASET_ROOT / f"{country}.parquet"
        if not pq_file.exists():
            print(f"  {country}: SKIPPED (no parquet at {pq_file})")
            continue
        rows = grid_sample_country(pq_file, target, rng)
        for r in rows:
            # Tag for visualization (defensive: parquet already has it).
            r["country"] = country
            r.pop("tags", None)
        sampled.extend(rows)
        print(f"  {country}: took {len(rows)} of {target} (pool {counts[country]:,})")

    # 4. Write the sample.
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w") as f:
        for row in sampled:
            f.write(json.dumps(row) + "\n")
    print(f"\nwrote {len(sampled)} polygons to {OUT_PATH}")


if __name__ == "__main__":
    main()

"""Sample-table renderers used by the dataset README.

Two main outputs:

1. **Size-bin distribution table** — counts polygons by ``size_bin``
   in a sample JSONL, then renders as a markdown table.

2. **Example row table** — picks a single representative row from
   the sample, looks up its full record in the per-country parquet,
   and renders all 13+ columns as a markdown table.

Both are pure read-only functions; they only read files.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

# Stable bin order (small < medium < large).
SIZE_BIN_ORDER: tuple[str, ...] = ("small", "medium", "large")


def truncate(s: str | None, max_len: int = 100) -> str:
    """Truncate ``s`` to ``max_len`` chars with a trailing ``...`` if cut."""
    if s is None:
        return ""
    s = str(s)
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def compute_sample_size_bin_distribution(
    sample_path: Path,
) -> list[tuple[str, int, float]]:
    """Count polygons by ``size_bin`` in the sample JSONL.

    Returns a list of ``(size_bin, count, pct)`` tuples in
    ``SIZE_BIN_ORDER``. ``pct`` is over the total rows in the file.
    Bins not present in the data get ``(bin, 0, 0.0)``.
    """
    counts: Counter[str] = Counter()
    total = 0
    if sample_path.is_file():
        with sample_path.open() as f:
            for line in f:
                row = json.loads(line)
                counts[row.get("size_bin", "")] += 1
                total += 1
    out: list[tuple[str, int, float]] = []
    for sb in SIZE_BIN_ORDER:
        n = counts.get(sb, 0)
        pct = round(n / total * 100.0, 1) if total > 0 else 0.0
        out.append((sb, n, pct))
    return out


def _aggregate_size_bin_column(table_or_column: pa.ChunkedArray) -> Counter[str]:
    """Run ``pc.value_counts`` on a single column and return a Counter.

    Skips rows with ``None`` values; for parquet schemas that don't
    have a ``size_bin`` column, callers should check the schema first.
    """
    vc = pc.value_counts(table_or_column)
    out: Counter[str] = Counter()
    try:
        values = vc.field("values").to_pylist()
        counts = vc.field("counts").to_pylist()
    except Exception:
        return out
    for v, c in zip(values, counts):
        if v is None:
            continue
        out[str(v)] = int(c)
    return out


def compute_global_size_bin_distribution(
    dataset_root: Path,
) -> list[tuple[str, int, float]]:
    """Compute the FULL-dataset ``size_bin`` distribution.

    Prefers ``combined/all_world.parquet`` (one read). Falls back to
    ``per_country/<country>/<country>.parquet`` files when combined
    is missing or unreadable. Per-country parquets without a
    ``size_bin`` column are skipped (older schemas).

    Returns a list of ``(size_bin, count, pct)`` tuples in
    ``SIZE_BIN_ORDER``. ``pct`` is over the sum of all bins.
    """
    combined = dataset_root / "combined" / "all_world.parquet"
    flat = dataset_root / "all_world.parquet"
    counts: Counter[str] = Counter()
    if combined.is_file():
        try:
            t = pq.read_table(combined, columns=["size_bin"])
            counts.update(_aggregate_size_bin_column(t["size_bin"]))
        except Exception:
            counts = Counter()
    if not counts and flat.is_file():
        # Flat layout produced by build_dataset.py before
        # organize_dataset.py has moved the combined parquet.
        try:
            t = pq.read_table(flat, columns=["size_bin"])
            counts.update(_aggregate_size_bin_column(t["size_bin"]))
        except Exception:
            counts = Counter()
    if not counts:
        # Fallback: aggregate per-country parquets that have size_bin.
        per_country_dir = dataset_root / "per_country"
        if per_country_dir.is_dir():
            for country_dir in sorted(per_country_dir.iterdir()):
                pq_path = country_dir / f"{country_dir.name}.parquet"
                if not pq_path.is_file():
                    continue
                try:
                    t = pq.read_table(pq_path, columns=["size_bin"])
                except Exception:
                    continue
                counts.update(_aggregate_size_bin_column(t["size_bin"]))
        # Also try the flat per-country layout (dataset/<country>.parquet).
        if not counts:
            for pq_path in sorted(dataset_root.glob("*.parquet")):
                if pq_path.name in ("all_world.parquet",):
                    continue
                try:
                    t = pq.read_table(pq_path, columns=["size_bin"])
                except Exception:
                    continue
                counts.update(_aggregate_size_bin_column(t["size_bin"]))

    total = sum(counts.values())
    out: list[tuple[str, int, float]] = []
    for sb in SIZE_BIN_ORDER:
        n = counts.get(sb, 0)
        pct = round(n / total * 100.0, 1) if total > 0 else 0.0
        out.append((sb, n, pct))
    return out


def build_size_bin_distribution_table(
    dist: list[tuple[str, int, float]],
) -> str:
    """Render the size-bin distribution as a markdown table."""
    out = "| size_bin | count | pct |\n|----------|-------|-----|\n"
    for sb, n, pct in dist:
        out += f"| {sb} | {n:,} | {pct:.1f}% |\n"
    total = sum(c for _, c, _ in dist)
    out += f"| **Total** | {total:,} | 100.0% |\n"
    return out


def pick_sample_row(
    sample_path: Path,
    prefer_country: str = "liechtenstein",
    prefer_tag_prefix: str = "natural=",
) -> dict | None:
    """Pick one representative row from the sample JSONL.

    Returns the first row where ``country == prefer_country`` AND
    ``matched_tag`` starts with ``prefer_tag_prefix``. Falls back
    to the first row of the requested country, then to the very
    first row in the file. Returns ``None`` if the file is empty
    or missing.
    """
    if not sample_path.is_file():
        return None
    first_row: dict | None = None
    country_fallback: dict | None = None
    with sample_path.open() as f:
        for line in f:
            row = json.loads(line)
            if first_row is None:
                first_row = row
            if row.get("country") == prefer_country:
                if country_fallback is None:
                    country_fallback = row
                if (row.get("matched_tag") or "").startswith(prefer_tag_prefix):
                    return row
    return country_fallback or first_row


def fetch_full_row_from_parquet(parquet_path: Path, osm_id: int) -> dict | None:
    """Look up ``osm_id`` in a per-country parquet and return the row.

    Returns ``None`` if the parquet is missing or the osm_id isn't
    found. The ``tags`` field is coerced to a list of strings for
    markdown rendering.
    """
    if not parquet_path.is_file():
        return None
    try:
        t = pq.read_table(parquet_path, filters=[("osm_id", "=", int(osm_id))])
    except Exception:
        return None
    if t.num_rows == 0:
        return None
    rec = t.to_pylist()[0]
    if rec.get("tags") is not None:
        rec["tags"] = [str(x) for x in rec["tags"]]
    return rec


def build_example_row_table(
    sample_path: Path,
    fallback_dir: Path | None = None,
    sample_row: dict | None = None,
) -> str:
    """Render a markdown table showing all columns of one row.

    Pipeline:
    1. ``pick_sample_row(sample_path)`` to find the row.
    2. ``fetch_full_row_from_parquet(<per_country>/<c>/<c>.parquet, osm_id)``
       to fill in the missing columns (the sample only has centroid-only).
    3. Render as a markdown table.
    """
    if sample_row is None:
        sample_row = pick_sample_row(sample_path)
    if sample_row is None:
        return (
            "*(no sample row available — run `scripts/sample_for_map.py` "
            "to generate `sample/sample_map.jsonl`)*\n"
        )

    # Resolve the full row from the per-country parquet when possible.
    full_row = sample_row
    if fallback_dir is not None:
        country = sample_row.get("country")
        osm_id = sample_row.get("osm_id")
        if country and osm_id is not None:
            pq_path = (
                fallback_dir / "per_country" / country / f"{country}.parquet"
            )
            fetched = fetch_full_row_from_parquet(pq_path, int(osm_id))
            if fetched is not None:
                full_row = fetched

    cols = [
        ("osm_id", full_row.get("osm_id")),
        ("osm_type", full_row.get("osm_type")),
        ("centroid_lon", full_row.get("centroid_lon")),
        ("centroid_lat", full_row.get("centroid_lat")),
        ("area_km2", full_row.get("area_km2")),
        ("tags", full_row.get("tags")),
        ("matched_tag", full_row.get("matched_tag")),
        ("continent", full_row.get("continent")),
        ("size_bin", full_row.get("size_bin")),
        ("country", full_row.get("country")),
        ("extract_status", full_row.get("extract_status")),
        ("pbf_date", full_row.get("pbf_date")),
        ("geometry_wkt", full_row.get("geometry_wkt")),
    ]
    out = "| column | value |\n|--------|-------|\n"
    for name, value in cols:
        if value is None:
            value_repr = "*(none)*"
        elif name == "area_km2" and isinstance(value, (int, float)):
            value_repr = f"{value:.4f}"
        elif name == "tags" and isinstance(value, list):
            value_repr = "<br>".join(f"`{t}`" for t in value) if value else "*(none)*"
        elif name == "geometry_wkt" and isinstance(value, str):
            value_repr = f"`{truncate(value, 100)}`"
        elif name in ("centroid_lon", "centroid_lat") and isinstance(value, (int, float)):
            value_repr = f"{value:.6f}"
        else:
            value_repr = f"`{value}`"
        out += f"| {name} | {value_repr} |\n"
    return out

"""Size-bin distribution computation.

Two flavors:
- :func:`compute_sample_size_bin_distribution`: counts polygons
  in the per-country sample JSONL.
- :func:`compute_global_size_bin_distribution`: counts over
  the full dataset (combined parquet, falls back to per-country
  parquets, falls back to flat-layout parquets).

Both return ``[(size_bin, count, pct), ...]`` in :data:`SIZE_BIN_ORDER`.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from osm_polygon_selection.io.pyarrow_compat import value_counts

# Stable bin order (small < medium < large).
SIZE_BIN_ORDER: tuple[str, ...] = ("small", "medium", "large")


def _aggregate_size_bin_column(table_or_column: pa.ChunkedArray) -> Counter[str]:
    """Run ``pc.value_counts`` on a single column and return a Counter.

    Skips rows with ``None`` values.
    """
    vc = value_counts(table_or_column)
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


def compute_sample_size_bin_distribution(
    sample_path: Path,
) -> list[tuple[str, int, float]]:
    """Count polygons by ``size_bin`` in the sample JSONL."""
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


def _read_combined_or_flat(dataset_root: Path) -> Counter[str]:
    combined = dataset_root / "combined" / "all_world.parquet"
    flat = dataset_root / "all_world.parquet"
    if combined.is_file():
        try:
            t = pq.read_table(combined, columns=["size_bin"])
            return _aggregate_size_bin_column(t["size_bin"])
        except Exception:
            pass
    if flat.is_file():
        try:
            t = pq.read_table(flat, columns=["size_bin"])
            return _aggregate_size_bin_column(t["size_bin"])
        except Exception:
            pass
    return Counter()


def _read_per_country(dataset_root: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
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
    if not counts:
        for pq_path in sorted(dataset_root.glob("*.parquet")):
            if pq_path.name == "all_world.parquet":
                continue
            try:
                t = pq.read_table(pq_path, columns=["size_bin"])
            except Exception:
                continue
            counts.update(_aggregate_size_bin_column(t["size_bin"]))
    return counts


def compute_global_size_bin_distribution(
    dataset_root: Path,
) -> list[tuple[str, int, float]]:
    """Compute the FULL-dataset ``size_bin`` distribution."""
    counts = _read_combined_or_flat(dataset_root)
    if not counts:
        counts = _read_per_country(dataset_root)
    total = sum(counts.values())
    out: list[tuple[str, int, float]] = []
    for sb in SIZE_BIN_ORDER:
        n = counts.get(sb, 0)
        pct = round(n / total * 100.0, 1) if total > 0 else 0.0
        out.append((sb, n, pct))
    return out


__all__ = [
    "SIZE_BIN_ORDER",
    "compute_global_size_bin_distribution",
    "compute_sample_size_bin_distribution",
]

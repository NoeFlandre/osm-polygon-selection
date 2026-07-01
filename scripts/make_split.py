"""Stratified train/val/test split for the published OSM polygon dataset.

Adds a ``split`` column (string, one of ``"train"`` / ``"val"`` /
``"test"``) to every per-country parquet in
``dataset/per_country/<country>/<country>.parquet`` and rebuilds the
combined ``dataset/combined/all_europe.parquet`` to include the new
column.

Stratification is **by country**: each country gets its rows
independently assigned to train/val/test using a single global RNG
seeded once and offset per country. The default ratios are 80/10/10.

Output:

- per-country parquets are rewritten in place with the new column
  appended (small row groups + page indexes for HF viewer compat).
- combined ``dataset/combined/all_europe.parquet`` is rewritten with
  the same small row groups.
- ``dataset/splits/split_manifest.json`` is written with the seed,
  ratios, stratify_by, total counts, and per-country counts.

Usage:

    uv run python scripts/make_split.py
    uv run python scripts/make_split.py --root /path/to/dataset --seed 42
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

# Default dataset root (external HDD).
DEFAULT_ROOT = Path("/Volumes/Seagate M3/osm-polygon-selection/dataset")

# Default split ratios. Must sum to 1.0; validated by tests.
DEFAULT_RATIOS: dict[str, float] = {"train": 0.8, "val": 0.1, "test": 0.1}

# Default seed. The tests pin this so the dataset's splits are
# reproducible across rebuilds.
DEFAULT_SEED = 42

# Target row group size for the rewritten parquets. With ~7.3M
# rows total, ~50k rows per group gives ~150 groups, each ~50-60 MB,
# well under HF's 300 MB scan limit.
ROW_GROUP_SIZE = 50_000

# The split column type.
_SPLIT_TYPE = pa.string()

# Stable order of split names (used by numpy.random.choice).
_SPLIT_NAMES = ("train", "val", "test")


# ---------------------------------------------------------------------------
# Pure helpers (no I/O)
# ---------------------------------------------------------------------------


def validate_ratios(ratios: dict[str, float]) -> None:
    """Assert the 3 split ratios sum to 1.0 within float epsilon.

    Also asserts exactly the 3 expected keys (train/val/test).
    """
    if set(ratios.keys()) != {"train", "val", "test"}:
        raise ValueError(
            f"ratios must have exactly the keys train/val/test; got {set(ratios.keys())}"
        )
    s = sum(ratios.values())
    if abs(s - 1.0) > 1e-9:
        raise ValueError(f"ratios must sum to 1.0; got {s}")


def assign_split_for_country(
    n_rows: int,
    country_index: int,
    seed: int,
    ratios: dict[str, float],
) -> np.ndarray:
    """Return a length-n_rows array of split names for one country.

    Pure: only uses numpy.random (deterministic for fixed inputs).

    The RNG is the global ``numpy.random.default_rng(seed)`` offset by
    the country index, so the overall split is deterministic across
    countries for a fixed seed (no per-country reseeding).
    """
    validate_ratios(ratios)
    rng = np.random.default_rng(seed + country_index)
    probs = np.array([ratios["train"], ratios["val"], ratios["test"]])
    choices = rng.choice(_SPLIT_NAMES, size=n_rows, p=probs)
    return choices


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def _read_manifest(root: Path) -> dict:
    return json.loads((root / "manifest.json").read_text())


def _add_split_column(parquet_path: Path, splits: np.ndarray) -> None:
    """Read a parquet, append the split column, rewrite in place.

    Uses ``pq.ParquetFile`` + ``table.append_column`` to avoid
    rewriting the entire file from scratch. Row groups are kept small
    (~50k rows) and page indexes enabled so the HF viewer can scan a
    single group without exceeding its 300 MB scan limit.
    """
    pf = pq.ParquetFile(parquet_path)
    table = pf.read()
    split_arr = pa.array(splits.tolist(), type=_SPLIT_TYPE)
    if "split" in table.schema.names:
        # Drop existing split column (re-run case) before re-appending.
        idx = table.schema.get_field_index("split")
        table = table.remove_column(idx)
    table = table.append_column("split", split_arr)
    pq.write_table(
        table,
        parquet_path,
        compression="snappy",
        row_group_size=ROW_GROUP_SIZE,
        write_page_index=True,
    )


def _write_combined(root: Path) -> int:
    """Rebuild combined/all_europe.parquet from per-country parquets.

    Returns the number of rows in the combined file.
    """
    manifest = _read_manifest(root)
    tables: list[pa.Table] = []
    for c_info in manifest["countries"]:
        c = c_info["country"]
        pq_path = root / "per_country" / c / f"{c}.parquet"
        if not pq_path.is_file():
            continue
        tables.append(pq.read_table(pq_path))
    if not tables:
        raise RuntimeError("no per-country parquets to combine")
    combined = pa.concat_tables(tables, promote_options="default")
    out = root / "combined" / "all_europe.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        combined,
        out,
        compression="snappy",
        row_group_size=ROW_GROUP_SIZE,
        write_page_index=True,
    )
    return combined.num_rows


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def make_split(
    root: Path = DEFAULT_ROOT,
    seed: int = DEFAULT_SEED,
    ratios: dict[str, float] | None = None,
) -> dict:
    """Run the full split pipeline. Returns the manifest dict.

    For each country in the manifest:
    - assign splits using a global RNG (seed + country_index)
    - append a ``split`` column to the per-country parquet
    Then rebuild combined/all_europe.parquet and write
    splits/split_manifest.json.

    Countries with zero polygons (recorded but no parquet) are
    counted as zero rows in the manifest and skipped in the parquet
    pass.
    """
    if ratios is None:
        ratios = DEFAULT_RATIOS
    validate_ratios(ratios)

    manifest = _read_manifest(root)
    per_country_counts: dict[str, dict[str, int]] = {}
    counts = {"train": 0, "val": 0, "test": 0}

    for idx, c_info in enumerate(manifest["countries"]):
        c = c_info["country"]
        n = int(c_info.get("n_polygons", 0))
        if n == 0:
            per_country_counts[c] = {"train": 0, "val": 0, "test": 0}
            continue

        pq_path = root / "per_country" / c / f"{c}.parquet"
        if not pq_path.is_file():
            print(f"  {c}: SKIP (no parquet at {pq_path})", file=sys.stderr)
            per_country_counts[c] = {"train": 0, "val": 0, "test": 0}
            continue

        splits = assign_split_for_country(n, idx, seed, ratios)
        _add_split_column(pq_path, splits)

        # Tally.
        unique, c_counts = np.unique(splits, return_counts=True)
        per_country_counts[c] = {k: 0 for k in _SPLIT_NAMES}
        for k, v in zip(unique, c_counts):
            per_country_counts[c][str(k)] = int(v)
            counts[str(k)] += int(v)
        print(
            f"  {c}: {n} rows -> "
            f"train={per_country_counts[c]['train']} "
            f"val={per_country_counts[c]['val']} "
            f"test={per_country_counts[c]['test']}"
        )

    # Rebuild combined parquet.
    n_combined = _write_combined(root)
    print(f"\ncombined/all_europe.parquet rebuilt with {n_combined:,} rows")

    out_manifest = {
        "seed": seed,
        "ratios": dict(ratios),
        "stratify_by": "country",
        "counts": counts,
        "per_country_counts": per_country_counts,
    }

    out_path = root / "splits" / "split_manifest.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_manifest, indent=2))
    print(f"{out_path} written")
    return out_manifest


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--root", type=Path, default=DEFAULT_ROOT,
        help=f"Dataset root (default: {DEFAULT_ROOT})",
    )
    p.add_argument(
        "--seed", type=int, default=DEFAULT_SEED,
        help=f"RNG seed (default: {DEFAULT_SEED})",
    )
    p.add_argument(
        "--train", type=float, default=DEFAULT_RATIOS["train"],
        help="Train ratio (default: 0.8)",
    )
    p.add_argument(
        "--val", type=float, default=DEFAULT_RATIOS["val"],
        help="Val ratio (default: 0.1)",
    )
    p.add_argument(
        "--test", type=float, default=DEFAULT_RATIOS["test"],
        help="Test ratio (default: 0.1)",
    )
    return p.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    ratios = {"train": args.train, "val": args.val, "test": args.test}
    out = make_split(root=args.root, seed=args.seed, ratios=ratios)
    print(json.dumps({"counts": out["counts"], "n_countries": len(out["per_country_counts"])}, indent=2))

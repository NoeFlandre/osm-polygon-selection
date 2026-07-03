"""Stratified train/val/test split for the published OSM polygon dataset.

Adds a ``split`` column (string, one of ``"train"`` / ``"val"`` /
``"test"``) to every per-country parquet in
``dataset/per_country/<country>/<country>.parquet`` and rebuilds the
combined ``dataset/combined/all_world.parquet`` to include the new
column.

Stratification is **by country**: each country gets its rows
independently assigned to train/val/test using a single global RNG
seeded once and offset per country. The default ratios are 80/10/10.

Output:

- per-country parquets are rewritten in place with the new column
  appended (small row groups + page indexes for HF viewer compat).
- combined ``dataset/combined/all_world.parquet`` is rewritten with
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

# Compression for the rewritten parquets. zstd level 1 gives
# ~36% better compression than snappy at ~12% slower encode,
# well within HF viewer's row group size limit.
COMPRESSION = "zstd"
COMPRESSION_LEVEL = 1

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
        compression=COMPRESSION,
        compression_level=COMPRESSION_LEVEL,
        row_group_size=ROW_GROUP_SIZE,
        write_page_index=True,
    )


def _add_split_column_streaming(parquet_path: Path, splits: np.ndarray) -> None:
    """Streaming alternative to ``_add_split_column``.

    Reads the source parquet one row group at a time, appends the
    pre-computed split column to each row group's table, and writes
    it back via ``ParquetWriter.write_batch``. Memory cost is
    O(ROW_GROUP_SIZE) per row group instead of O(table size).

    The output schema matches ``_add_split_column``: same data + a
    trailing ``split`` (string) column, with small row groups and
    page indexes enabled.
    """
    import os
    import tempfile

    src = pq.ParquetFile(parquet_path)
    base_schema = src.schema_arrow
    has_split = "split" in base_schema.names
    if has_split:
        # Re-run case: drop split from the schema so the new column
        # can be appended freshly.
        new_fields = [f for f in base_schema if f.name != "split"]
        new_schema = pa.schema(new_fields + [pa.field("split", _SPLIT_TYPE)])
    else:
        new_schema = base_schema.append(pa.field("split", _SPLIT_TYPE))

    # Write to a sibling tempfile, then atomically rename.
    tmp_dir = parquet_path.parent
    fd, tmp_path = tempfile.mkstemp(
        prefix=".split_", suffix=".parquet", dir=str(tmp_dir),
    )
    os.close(fd)
    try:
        writer = pq.ParquetWriter(
            tmp_path,
            new_schema,
            compression=COMPRESSION,
            compression_level=COMPRESSION_LEVEL,
            write_page_index=True,
        )
        try:
            offset = 0
            for rg_idx in range(src.num_row_groups):
                # Read one row group (all columns, including any pre-existing
                # split). Memory cost is bounded by the row group size.
                # read_row_group returns a Table, which we convert to a
                # RecordBatch for write_batch.
                tbl = src.read_row_group(rg_idx)
                batch = pa.RecordBatch.from_arrays(
                    [tbl.column(i).combine_chunks() for i in range(tbl.num_columns)],
                    schema=tbl.schema,
                )
                rg_rows = batch.num_rows
                rg_splits = pa.array(
                    splits[offset:offset + rg_rows].tolist(), type=_SPLIT_TYPE,
                )
                if has_split:
                    # Drop the existing split column.
                    idx = batch.schema.get_field_index("split")
                    batch = batch.remove_column(idx)
                batch = batch.append_column("split", rg_splits)
                # Truncate to ROW_GROUP_SIZE chunks so HF viewer stays
                # within its 300 MB scan limit per row group.
                pos = 0
                while pos < rg_rows:
                    end = min(pos + ROW_GROUP_SIZE, rg_rows)
                    writer.write_batch(batch.slice(pos, end - pos))
                    pos = end
                offset += rg_rows
        finally:
            writer.close()
        os.replace(tmp_path, parquet_path)
    except Exception:
        if Path(tmp_path).is_file():
            os.unlink(tmp_path)
        raise


def _write_combined(root: Path) -> int:
    """Rebuild combined/all_world.parquet from per-country parquets.

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
    out = root / "combined" / "all_world.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        combined,
        out,
        compression=COMPRESSION,
        compression_level=COMPRESSION_LEVEL,
        row_group_size=ROW_GROUP_SIZE,
        write_page_index=True,
    )
    return combined.num_rows


def _write_combined_streaming(
    root: Path,
    *,
    seed: int = DEFAULT_SEED,
    ratios: dict[str, float] | None = None,
    manifest: dict | None = None,
) -> int:
    """Streaming alternative to ``_write_combined``.

    Concatenates per-country parquets WITHOUT materializing them all
    in memory: walks each parquet's row groups in order and writes
    them one at a time to ``combined/all_world.parquet`` via
    ``ParquetWriter.write_batch``.

    The combined parquet has the same columns as the per-country
    parquets PLUS a trailing ``split`` column. Each row group
    receives its slice of the deterministic split assignment
    (``assign_split_for_country(country_index, seed, ratios)``) so
    per-row split membership is consistent with
    ``split_manifest.json``.

    Per-country parquets are NEVER rewritten here. The split column
    is only persisted in the combined file.

    Returns the number of rows written.
    """
    import os
    import tempfile

    if ratios is None:
        ratios = DEFAULT_RATIOS
    if manifest is None:
        manifest = _read_manifest(root)

    # Use the schema of the first non-empty per-country parquet, plus
    # a trailing 'split' column. Per-country parquets may already have
    # a legacy `split` column from previous runs (before the
    # optimization that stopped rewriting them) -- strip it from the
    # output schema so we don't end up with duplicates.
    base_schema = None
    for c_info in manifest["countries"]:
        c = c_info["country"]
        pq_path = root / "per_country" / c / f"{c}.parquet"
        if pq_path.is_file():
            base_schema = pq.read_schema(pq_path)
            break
    if base_schema is None:
        raise RuntimeError("no per-country parquets to combine")

    if "split" in base_schema.names:
        base_schema = pa.schema(
            [f for f in base_schema if f.name != "split"],
        )
    combined_schema = base_schema.append(pa.field("split", _SPLIT_TYPE))

    out = root / "combined" / "all_world.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=".combined_", suffix=".parquet", dir=str(out.parent),
    )
    os.close(fd)
    total_rows = 0
    try:
        writer = pq.ParquetWriter(
            tmp_path,
            combined_schema,
            compression=COMPRESSION,
            compression_level=COMPRESSION_LEVEL,
            write_page_index=True,
        )
        try:
            for idx, c_info in enumerate(manifest["countries"]):
                c = c_info["country"]
                pq_path = root / "per_country" / c / f"{c}.parquet"
                if not pq_path.is_file():
                    continue
                src = pq.ParquetFile(pq_path)
                n_rows = sum(
                    src.metadata.row_group(i).num_rows
                    for i in range(src.num_row_groups)
                )
                # Deterministic split for this country.
                splits = assign_split_for_country(
                    n_rows, idx, seed, ratios,
                )
                row_offset = 0
                for rg_idx in range(src.num_row_groups):
                    # Read one row group (per-country data).
                    tbl = src.read_row_group(rg_idx)
                    batch = pa.RecordBatch.from_arrays(
                        [tbl.column(i).combine_chunks() for i in range(tbl.num_columns)],
                        schema=tbl.schema,
                    )
                    # Strip any legacy `split` column from previous runs.
                    if "split" in batch.schema.names:
                        idx = batch.schema.get_field_index("split")
                        batch = batch.remove_column(idx)
                    rg_rows = batch.num_rows
                    rg_splits = pa.array(
                        splits[row_offset:row_offset + rg_rows].tolist(),
                        type=_SPLIT_TYPE,
                    )
                    batch = batch.append_column("split", rg_splits)
                    # Re-chunk the row group into smaller slices so the
                    # combined file respects ROW_GROUP_SIZE (HF viewer
                    # wants < 300 MB per row group).
                    pos = 0
                    while pos < rg_rows:
                        end = min(pos + ROW_GROUP_SIZE, rg_rows)
                        writer.write_batch(batch.slice(pos, end - pos))
                        pos = end
                    row_offset += rg_rows
                    total_rows += rg_rows
        finally:
            writer.close()
        os.replace(tmp_path, out)
    except Exception:
        if Path(tmp_path).is_file():
            os.unlink(tmp_path)
        raise
    return total_rows


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def make_split(
    root: Path = DEFAULT_ROOT,
    seed: int = DEFAULT_SEED,
    ratios: dict[str, float] | None = None,
) -> dict:
    """Run the full split pipeline. Returns the manifest dict.

    The split is deterministic from ``(seed, country_index, n_rows)``.
    Per-country parquets are NEVER rewritten -- only the combined
    parquet gets a trailing ``split`` column. The split_manifest.json
    records the per-country counts so downstream readers can verify
    membership without re-walking the combined file.

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

    # Pre-compute splits for each country (deterministic from seed +
    # country_index) so we can tally without re-reading parquets.
    for idx, c_info in enumerate(manifest["countries"]):
        c = c_info["country"]
        n = int(c_info.get("n_polygons", 0))
        if n == 0:
            per_country_counts[c] = {"train": 0, "val": 0, "test": 0}
            continue

        splits = assign_split_for_country(n, idx, seed, ratios)
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

    # Rebuild combined parquet (only place that persists `split`).
    n_combined = _write_combined_streaming(
        root, seed=seed, ratios=ratios, manifest=manifest,
    )
    print(f"\ncombined/all_world.parquet rebuilt with {n_combined:,} rows")

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
    # Only count alive countries (those with non-zero polygons);
    # countries with n_polygons==0 are recorded in the manifest as
    # killed but shouldn't be in the split count.
    n_alive = sum(1 for c in out["per_country_counts"].values()
                  if sum(c.values()) > 0)
    print(json.dumps({"counts": out["counts"], "n_countries": n_alive}, indent=2))

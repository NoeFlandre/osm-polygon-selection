"""Split pipeline constants and ratio validation.

All defaults are sourced from a single location so callers can
override behavior without duplicating constants. Pure module:
no I/O, no numpy state.
"""

from __future__ import annotations

from typing import Mapping, TypedDict

import pyarrow as pa

from osm_polygon_selection.config import RuntimeConfig

# Default dataset root (from RuntimeConfig; honors $OSM_DATA_ROOT).
DEFAULT_ROOT = RuntimeConfig.from_env().dataset_root

# Default split ratios. Must sum to 1.0; validated by validate_ratios.
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
SPLIT_TYPE = pa.string()

# Stable order of split names (used by numpy.random.choice).
SPLIT_NAMES = ("train", "val", "test")


class SplitRatios(TypedDict):
    """Mapping of split name to its proportion. Must sum to 1.0."""

    train: float
    val: float
    test: float


def validate_ratios(ratios: Mapping[str, float]) -> None:
    """Assert the 3 split ratios sum to 1.0 within float epsilon.

    Also asserts exactly the 3 expected keys (train/val/test).
    """
    keys = set(ratios.keys())
    expected = {"train", "val", "test"}
    if keys != expected:
        raise ValueError(
            f"ratios must have exactly the keys {sorted(expected)}; got {sorted(keys)}"
        )
    s = sum(ratios.values())
    if abs(s - 1.0) > 1e-9:
        raise ValueError(f"ratios must sum to 1.0; got {s}")


__all__ = [
    "COMPRESSION",
    "COMPRESSION_LEVEL",
    "DEFAULT_RATIOS",
    "DEFAULT_ROOT",
    "DEFAULT_SEED",
    "ROW_GROUP_SIZE",
    "SPLIT_NAMES",
    "SPLIT_TYPE",
    "SplitRatios",
    "validate_ratios",
]

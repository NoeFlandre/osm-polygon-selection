"""Train/val/test split package.

Owns the deterministic per-country stratified split pipeline. The
combined parquet gets a trailing ``split`` column; per-country
parquets are NEVER rewritten (deliberate perf optimization).
"""

from osm_polygon_selection.dataset_split.assignment import assign_split_for_country
from osm_polygon_selection.dataset_split.combined import write_combined_streaming
from osm_polygon_selection.dataset_split.config import (
    COMPRESSION,
    COMPRESSION_LEVEL,
    DEFAULT_RATIOS,
    DEFAULT_ROOT,
    DEFAULT_SEED,
    ROW_GROUP_SIZE,
    SPLIT_NAMES,
    SPLIT_TYPE,
    SplitRatios,
    validate_ratios,
)
from osm_polygon_selection.dataset_split.manifest import (
    build_split_manifest,
    read_dataset_manifest,
    write_split_manifest,
)
from osm_polygon_selection.dataset_split.runner import make_split

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
    "assign_split_for_country",
    "build_split_manifest",
    "make_split",
    "read_dataset_manifest",
    "validate_ratios",
    "write_combined_streaming",
    "write_split_manifest",
]

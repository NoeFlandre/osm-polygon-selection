"""Public API for the sampling pipeline.

Layout:
- :mod:`config` — power-law allocation constants and ``SamplingConfig``
- :mod:`discovery` — manifest + dataset root lookup
- :mod:`grid` — bbox + grid cell assignment + reservoir sampling
- :mod:`rows` — parquet lookup + JSONL output
- :mod:`runner` — orchestration
"""

from osm_polygon_selection.sampling.config import (
    ALL_COLS,
    CAP,
    FLOOR,
    GEO_COLS,
    POWER,
    SAMPLE_RNG_SEED,
    SamplingConfig,
    power_law_alloc,
)
from osm_polygon_selection.sampling.discovery import (
    counts_from_processed,
    find_manifest_and_dataset_root,
)
from osm_polygon_selection.sampling.grid import grid_sample_country
from osm_polygon_selection.sampling.rows import (
    find_country_parquet,
    tag_and_strip,
    write_jsonl,
)
from osm_polygon_selection.sampling.runner import (
    DEFAULT_OUT_PATH,
    run_sample_for_map,
)

__all__ = [
    "ALL_COLS",
    "CAP",
    "DEFAULT_OUT_PATH",
    "FLOOR",
    "GEO_COLS",
    "POWER",
    "SAMPLE_RNG_SEED",
    "SamplingConfig",
    "counts_from_processed",
    "find_country_parquet",
    "find_manifest_and_dataset_root",
    "grid_sample_country",
    "power_law_alloc",
    "run_sample_for_map",
    "tag_and_strip",
    "write_jsonl",
]

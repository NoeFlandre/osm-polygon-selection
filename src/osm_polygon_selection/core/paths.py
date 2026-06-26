"""Centralized path resolution for data files.

Heavy data (PBFs, large processed JSONLs) typically lives outside the
repo on an external drive. Scripts read paths from CLI args or from the
OSM_DATA_ROOT env var. The fallback is the local `data/` directory.

Layout (relative to OSM_DATA_ROOT, default `./data`):

    raw/                          downloaded PBF files
    reference/                    static reference data (shapefiles, etc.)
    processed/<region>/           pipeline outputs, one subdir per region
    whitelist.json                global whitelist (built from reference)
"""

import os
from pathlib import Path


def data_root() -> Path:
    """Base data directory. OSM_DATA_ROOT env var if set, else ./data."""
    if env := os.environ.get("OSM_DATA_ROOT"):
        return Path(env)
    return Path("data")


def raw_path(filename: str) -> Path:
    """Path under raw/."""
    return data_root() / "raw" / filename


def reference_path(subdir: str) -> Path:
    """Path under reference/<subdir>."""
    return data_root() / "reference" / subdir


def processed_path(region: str, filename: str) -> Path:
    """Path under processed/<region>/."""
    return data_root() / "processed" / region / filename


def whitelist_path() -> Path:
    """Path to the global whitelist.json."""
    return data_root() / "whitelist.json"

"""Sample-for-map CLI: build a small parquet sample for folium previewing."""

from __future__ import annotations

import sys
from pathlib import Path

from osm_polygon_selection.config import RuntimeConfig
from osm_polygon_selection.config.paths import dataset_root
from osm_polygon_selection.sampling import DEFAULT_OUT_PATH, run_sample_for_map


PROCESSED_ROOT = RuntimeConfig.from_env().processed_root


def main() -> None:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT_PATH
    run_sample_for_map(PROCESSED_ROOT, out_path=out_path)


__all__ = ["PROCESSED_ROOT", "dataset_root", "main"]


if __name__ == "__main__":
    main()

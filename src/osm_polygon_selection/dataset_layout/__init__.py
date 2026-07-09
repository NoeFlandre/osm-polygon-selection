"""Dataset directory layout helpers.

Public-facing layout is::

    dataset/
    ├── README.md, manifest.json, metadata.yaml       (root landing page)
    ├── per_country/<country>/{<country>.parquet, README.md}
    ├── combined/{all_world.parquet, README.md}
    ├── sample/{sample_map.jsonl, README.md}
    ├── preview/{map_preview.png, README.md}
    └── splits/{split_manifest.json}

These helpers create the subfolder skeleton and move/copy files
into it. They are pure file-system operations: no JSON parsing,
no pyarrow, no remote API calls.
"""

from osm_polygon_selection.dataset_layout.helpers import (
    ROOT_KEPT_FILES,
    SUBFOLDERS,
    cleanup_loose_root_files,
    ensure_layout,
    human_size,
    move_combined,
    move_country_files,
    move_preview,
    move_sample,
)

__all__ = [
    "ROOT_KEPT_FILES",
    "SUBFOLDERS",
    "cleanup_loose_root_files",
    "ensure_layout",
    "human_size",
    "move_combined",
    "move_country_files",
    "move_preview",
    "move_sample",
]

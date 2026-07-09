"""Manifest and dataset-root discovery for the sampling pipeline.

Locates ``manifest.json`` (the build_dataset output) across the
candidate dataset roots (env override, default sibling-of-repo,
common external-HDD locations). Falls back to walking
``$PROCESSED_ROOT`` and counting JSONL lines per country.
"""

from __future__ import annotations

import json
from pathlib import Path

from osm_polygon_selection.config import dataset_root

EXTRA_ROOTS: tuple[Path, ...] = (
    Path("/Volumes/Seagate M3/osm-polygon-selection/dataset"),
    Path("/Volumes/Seagate M3/osm-polygon-selection-dataset"),
)


def find_manifest_and_dataset_root() -> tuple[Path, dict] | tuple[None, None]:
    """Locate the manifest.json and the dataset root.

    Tries, in order:
    1. ``$OSM_DATASET_DIR/manifest.json`` (explicit env override).
    2. The default sibling-of-repo path (``osm-polygon-selection-dataset/``).
    3. Common external-HDD locations.

    Returns ``(root, manifest_dict)`` or ``(None, None)`` if no
    manifest was found.
    """
    candidates: list[Path] = [dataset_root(), *EXTRA_ROOTS]
    for root in candidates:
        manifest = root / "manifest.json"
        if manifest.is_file():
            return root, json.loads(manifest.read_text())
    return None, None


def counts_from_processed(processed_root: Path) -> dict[str, int]:
    """Fall back to walking ``$PROCESSED_ROOT`` when no manifest exists.

    Counts rows in each ``03_classified.jsonl`` file.
    """
    counts: dict[str, int] = {}
    for country_dir in sorted(processed_root.iterdir()):
        if not country_dir.is_dir():
            continue
        classified = country_dir / "03_classified.jsonl"
        if not classified.exists():
            continue
        counts[country_dir.name] = sum(1 for _ in classified.open())
    return counts

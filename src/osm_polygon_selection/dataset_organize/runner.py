"""Orchestration for the dataset_organize pipeline.

Wires together:
- :mod:`osm_polygon_selection.dataset_layout` — move / copy / cleanup
- :mod:`.manifests` — manifest read / update
- :mod:`.readmes` — README writers (delegating to ``osm_polygon_selection.readme``)
"""

from __future__ import annotations

import json
from pathlib import Path

from osm_polygon_selection.dataset_layout import (
    cleanup_loose_root_files,
    ensure_layout,
    move_combined,
    move_country_files,
    move_preview,
    move_sample,
)

from osm_polygon_selection.dataset_organize.manifests import load_manifest
from osm_polygon_selection.dataset_organize.readmes import (
    update_root_readme,
    write_country_readmes,
    write_folder_readmes,
)

DEFAULT_ROOT = Path("/Volumes/Seagate M3/osm-polygon-selection/dataset")
DEFAULT_SAMPLE_SRC = Path("/tmp/sample_map.jsonl")
DEFAULT_PREVIEW_SRC = Path(
    "/Users/noeflandre/osm-polygon-selection/data/dataset/map_preview.png"
)


def run_organize(
    root: Path = DEFAULT_ROOT,
    sample_src: Path | None = None,
    preview_src: Path | None = None,
) -> dict:
    """Run the full layout transformation. Returns a summary dict."""
    if not root.is_dir():
        raise SystemExit(f"dataset root does not exist: {root}")
    if not (root / "manifest.json").is_file():
        raise SystemExit(f"missing manifest.json at {root}")

    summary: dict = {"root": str(root), "steps": []}

    ensure_layout(root)
    summary["steps"].append("ensure_layout")

    manifest = load_manifest(root)
    country_names = [c["country"] for c in manifest["countries"]]
    summary["n_countries"] = len(country_names)

    summary["countries_moved"] = move_country_files(root, country_names)
    summary["steps"].append("move_country_files")

    summary["combined_moved"] = move_combined(root)
    summary["steps"].append("move_combined")

    summary["sample_copied"] = move_sample(root, sample_src or DEFAULT_SAMPLE_SRC)
    summary["steps"].append("move_sample")

    summary["preview_copied"] = move_preview(root, preview_src or DEFAULT_PREVIEW_SRC)
    summary["steps"].append("move_preview")

    summary["country_readmes_written"] = write_country_readmes(root, manifest)
    summary["steps"].append("write_country_readmes")

    summary["folder_readmes_written"] = write_folder_readmes(root, manifest)
    summary["steps"].append("write_folder_readmes")

    update_root_readme(root)
    summary["root_readme_written"] = True
    summary["steps"].append("update_root_readme")

    summary["loose_root_files_removed"] = cleanup_loose_root_files(root)
    summary["steps"].append("cleanup_loose_root_files")

    return summary

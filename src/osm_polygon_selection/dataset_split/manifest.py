"""Manifest IO + split-manifest construction.

The split manifest records the seed, ratios, stratify_by key,
total counts, and per-country counts. The dataset manifest
(``manifest.json``) is read but never mutated by this package.
"""

from __future__ import annotations

import json
from pathlib import Path

from osm_polygon_selection.dataset_split.config import SPLIT_NAMES


def read_dataset_manifest(root: Path) -> dict:
    """Read the dataset manifest.json. Pure file IO."""
    return json.loads((root / "manifest.json").read_text())


def build_split_manifest(
    seed: int,
    ratios: dict[str, float],
    per_country_counts: dict[str, dict[str, int]],
) -> dict:
    """Construct the split_manifest.json payload (no IO).

    The shape is exactly:
      {
        "seed": int,
        "ratios": dict[str, float],
        "stratify_by": "country",
        "counts": dict[str, int],
        "per_country_counts": dict[str, dict[str, int]],
      }
    """
    counts = {k: 0 for k in SPLIT_NAMES}
    for c_counts in per_country_counts.values():
        for k, v in c_counts.items():
            counts[k] = counts.get(k, 0) + int(v)
    return {
        "seed": seed,
        "ratios": dict(ratios),
        "stratify_by": "country",
        "counts": counts,
        "per_country_counts": per_country_counts,
    }


def write_split_manifest(root: Path, payload: dict) -> Path:
    """Write the split manifest under ``<root>/splits/split_manifest.json``.

    Returns the path written.
    """
    out_path = root / "splits" / "split_manifest.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2))
    return out_path


__all__ = [
    "build_split_manifest",
    "read_dataset_manifest",
    "write_split_manifest",
]

"""Manifest read / update helpers for the dataset_organize pipeline."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def load_manifest(root: Path) -> dict:
    """Load the dataset's manifest.json."""
    return json.loads((root / "manifest.json").read_text())


def maybe_load_split_counts(root: Path) -> tuple[dict[str, int], int | str]:
    """Return ``(counts, seed)`` from ``splits/split_manifest.json``.

    Returns empty counts and seed=42 if no split manifest is present.
    """
    split_manifest_path = root / "splits" / "split_manifest.json"
    if not split_manifest_path.is_file():
        return {}, 42
    with split_manifest_path.open() as f:
        sm = json.load(f)
    return sm.get("counts", {}), sm.get("seed", 42)


def status_line(countries: list[dict]) -> str:
    """Render the dataset's status line for the root README."""
    n_clean = sum(1 for c in countries if c["extract_status"] == "clean")
    n_killed = len(countries) - n_clean
    if n_killed == 0:
        return f"All {n_clean} geographic units are extracted end-to-end."
    return (
        f"{n_clean} of {len(countries)} geographic units are clean. "
        f"{n_killed} unit(s) were killed mid-pipeline "
        f"(see [`per_country/<unit>/README.md`](./per_country/))."
    )


def now_iso() -> str:
    """Current time in ISO format (re-exported for tests)."""
    return datetime.now().isoformat()

"""Per-country deterministic split assignment.

Pure module: no I/O, no global numpy state. Determinism comes
from seeding ``numpy.random.default_rng(seed + country_index)``
per call.
"""

from __future__ import annotations

from typing import Mapping

import numpy as np

from osm_polygon_selection.dataset_split.config import (
    SPLIT_NAMES,
    validate_ratios,
)


def assign_split_for_country(
    n_rows: int,
    country_index: int,
    seed: int,
    ratios: Mapping[str, float],
) -> np.ndarray:
    """Return a length-n_rows array of split names for one country.

    Pure: only uses numpy.random (deterministic for fixed inputs).

    The RNG is ``numpy.random.default_rng(seed)`` offset by
    country_index, so the overall split is deterministic across
    countries for a fixed seed (no per-country reseeding).
    """
    validate_ratios(ratios)
    rng = np.random.default_rng(seed + country_index)
    probs = np.array([ratios["train"], ratios["val"], ratios["test"]])
    choices = rng.choice(SPLIT_NAMES, size=n_rows, p=probs)
    return choices


__all__ = ["assign_split_for_country"]

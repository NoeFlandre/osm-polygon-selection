"""Configuration for the dataset sample-for-map pipeline.

Holds the power-law allocation constants and the parquet column
list. The runner instantiates a ``SamplingConfig`` to plumb
these values into the grid sampler.
"""

from __future__ import annotations

from dataclasses import dataclass

# Per-country floor and cap. Floor ensures small countries show up;
# cap prevents one country from dominating the map.
FLOOR = 8          # every country gets at least this many
CAP = 200          # never more than this per country
POWER = 0.4        # power-law compression exponent

# Parquet columns we read. Mirrors what visualize.py reads.
GEO_COLS = ["centroid_lon", "centroid_lat"]
ALL_COLS = GEO_COLS + [
    "osm_id", "area_km2", "continent",
    "size_bin", "matched_tag", "country",
]

SAMPLE_RNG_SEED = 42


@dataclass(frozen=True)
class SamplingConfig:
    """Inputs to the per-country sample allocation."""

    floor: int = FLOOR
    cap: int = CAP
    power: float = POWER


def power_law_alloc(country_counts: dict[str, int], cfg: SamplingConfig | None = None) -> dict[str, int]:
    """Allocate target sample size per country using power-law compression.

    ``n_target = clamp(round(n_polygons ** POWER), FLOOR, CAP)``
    """
    cfg = cfg or SamplingConfig()
    return {
        c: max(cfg.floor, min(cfg.cap, round(count ** cfg.power)))
        for c, count in country_counts.items()
    }

"""PBF download helpers (curl wrappers) for operator scripts.

Wraps ``curl`` invocations against Geofabrik. Returns the local
path of the downloaded PBF. Does NOT run the download itself;
the caller passes the built command to :mod:`subprocess`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence


def build_curl_command(url: str, target: Path, *, timeout_s: int = 600) -> list[str]:
    """Build the curl invocation for a Geofabrik PBF."""
    return ["curl", "-L", "-s", "-o", str(target), url, "--max-time", str(timeout_s)]


def pbf_is_present(target: Path, *, min_size_bytes: int = 1000) -> bool:
    """True if ``target`` exists and exceeds the size threshold."""
    if not target.exists():
        return False
    return target.stat().st_size > min_size_bytes


def pbf_size_mb(pbf: Path) -> float:
    return pbf.stat().st_size / 1024 / 1024


def region_pbf_name(region: str) -> str:
    return f"{region}-latest.osm.pbf"


def geofabrik_region_url(country: str, region: str) -> str:
    """Build the Geofabrik URL for a regional sub-PBF."""
    pbf_name = region_pbf_name(region)
    return f"https://download.geofabrik.de/europe/{country}/{pbf_name}"


def geofabrik_country_url(country: str) -> str:
    """Build the Geofabrik URL for a country-level PBF."""
    return f"https://download.geofabrik.de/europe/{country}-latest.osm.pbf"


__all__ = [
    "build_curl_command",
    "geofabrik_country_url",
    "geofabrik_region_url",
    "pbf_is_present",
    "pbf_size_mb",
    "region_pbf_name",
]

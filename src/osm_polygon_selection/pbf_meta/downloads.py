"""PBF download + date helpers.

Pure functions over Geofabrik URLs and on-disk PBF mtimes.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from osm_polygon_selection.pbf_meta.regions import (
    SUB_REGION_PARENTS,
    US_GEOFABRIK_REGIONS,
)
from osm_polygon_selection.pbf_meta.sources import NON_EUROPE_COUNTRIES

# Default raw-PBF directory on the external HDD. Can be overridden
# by passing a custom ``raw_dir`` to :func:`pbf_date_for`.
DEFAULT_RAW_DIR = Path("/Volumes/Seagate M3/osm-polygon-selection/raw")


def geofabrik_url(country: str) -> str:
    """Return the Geofabrik overview URL for a country.

    Geofabrik organizes extracts into continent-scale subtrees
    (e.g. ``/europe/``, ``/africa/``). Most countries live under
    ``/europe/``; the few exceptions are listed in
    ``NON_EUROPE_COUNTRIES``.

    Some large countries are split into sub-regions to keep each
    PBF manageable. The slug convention is ``<country>-<region>``
    and the URL pattern is ``/asia/<country>/<region>``,
    ``/south-america/<country>/<region>``, or
    ``/north-america/us/<state>`` (US states nest under ``us/``).
    """
    for parent in SUB_REGION_PARENTS:
        if country.startswith(f"{parent}-"):
            region = country[len(parent) + 1:]
            continent = NON_EUROPE_COUNTRIES.get(country, "asia")
            return (
                f"https://download.geofabrik.de/{continent}/"
                f"{parent}/{region}.html"
            )
    if country.startswith("russia-"):
        region = country[len("russia-"):]
        return f"https://download.geofabrik.de/russia/{region}.html"
    if country.startswith("us-"):
        rest = country[len("us-"):]
        if rest in US_GEOFABRIK_REGIONS:
            continent = NON_EUROPE_COUNTRIES.get(country, "north-america")
            return (
                f"https://download.geofabrik.de/{continent}/{country}.html"
            )
        continent = NON_EUROPE_COUNTRIES.get(country, "north-america")
        return f"https://download.geofabrik.de/{continent}/us/{rest}.html"
    region = NON_EUROPE_COUNTRIES.get(country, "europe")
    return f"https://download.geofabrik.de/{region}/{country}.html"


def format_pbf_date(raw: str) -> str:
    """Normalize a PBF date string to YYYY-MM-DD or 'unknown'."""
    if not raw or raw == "unknown":
        return "unknown"
    return raw


def pbf_date_for(country: str, raw_dir: Path = DEFAULT_RAW_DIR) -> str:
    """Return the mtime of ``<country>-latest.osm.pbf`` as YYYY-MM-DD.

    Returns "unknown" if the PBF doesn't exist at the conventional
    location.
    """
    pbf = raw_dir / f"{country}-latest.osm.pbf"
    if not pbf.is_file():
        return "unknown"
    mtime = pbf.stat().st_mtime
    return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")


__all__ = [
    "DEFAULT_RAW_DIR",
    "format_pbf_date",
    "geofabrik_url",
    "pbf_date_for",
]

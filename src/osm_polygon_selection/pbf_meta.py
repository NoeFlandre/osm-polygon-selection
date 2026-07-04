"""PBF metadata: dates and Geofabrik URLs.

Tiny helpers used by the build/publish pipeline to record provenance
on each country (when the source PBF was fetched, where it came from).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

# Default raw-PBF directory on the external HDD.
DEFAULT_RAW_DIR = Path("/Volumes/Seagate M3/osm-polygon-selection/raw")

# Countries outside the /europe/ Geofabrik tree. Add new regions
# here as we expand the project. The URL pattern is
# ``https://download.geofabrik.de/<region>/<country>.html``.
NON_EUROPE_COUNTRIES: dict[str, str] = {
    # North Africa
    "morocco": "africa",
    "tunisia": "africa",
    "algeria": "africa",
    "libya": "africa",
    "egypt": "africa",
    # West Africa
    "senegal-and-gambia": "africa",
    "guinea-bissau": "africa",
    "guinea": "africa",
    "sierra-leone": "africa",
    "liberia": "africa",
    "ivory-coast": "africa",
    "ghana": "africa",
    "togo": "africa",
    "benin": "africa",
    "burkina-faso": "africa",
    "mali": "africa",
    "mauritania": "africa",
    "niger": "africa",
    "nigeria": "africa",
    # Central Africa
    "cameroon": "africa",
    "central-african-republic": "africa",
    "chad": "africa",
    "congo-brazzaville": "africa",
    "congo-democratic-republic": "africa",
    "equatorial-guinea": "africa",
    "gabon": "africa",
    # East Africa
    "burundi": "africa",
    "comores": "africa",
    "djibouti": "africa",
    "eritrea": "africa",
    "ethiopia": "africa",
    "kenya": "africa",
    "rwanda": "africa",
    "seychelles": "africa",
    "somalia": "africa",
    "south-sudan": "africa",
    "sudan": "africa",
    "tanzania": "africa",
    "uganda": "africa",
    "mauritius": "africa",
    "madagascar": "africa",
    # Southern Africa
    "angola": "africa",
    "botswana": "africa",
    "lesotho": "africa",
    "malawi": "africa",
    "mozambique": "africa",
    "namibia": "africa",
    "south-africa": "africa",
    "swaziland": "africa",
    "zambia": "africa",
    "zimbabwe": "africa",
    # Island territories
    "canary-islands": "africa",
    "sao-tome-and-principe": "africa",
    "saint-helena-ascension-and-tristan-da-cunha": "africa",
    "mayotte": "africa",
    # South America
    "argentina": "south-america",
    "bolivia": "south-america",
    "brazil": "south-america",
    "brazil-norte": "south-america",
    "brazil-centro-oeste": "south-america",
    "brazil-nordeste": "south-america",
    "brazil-sudeste": "south-america",
    "brazil-sul": "south-america",
    "chile": "south-america",
    "colombia": "south-america",
    "ecuador": "south-america",
    "guyana": "south-america",
    "paraguay": "south-america",
    "peru": "south-america",
    "suriname": "south-america",
    "uruguay": "south-america",
    "venezuela": "south-america",
}


def geofabrik_url(country: str) -> str:
    """Return the Geofabrik overview URL for a country.

    Geofabrik organizes extracts into continent-scale subtrees
    (e.g. ``/europe/``, ``/africa/``). Most of our countries
    live under ``/europe/``; the few exceptions are listed in
    ``NON_EUROPE_COUNTRIES``.
    """
    region = NON_EUROPE_COUNTRIES.get(country, "europe")
    return f"https://download.geofabrik.de/{region}/{country}.html"


def format_pbf_date(raw: str) -> str:
    """Normalize a PBF date string to YYYY-MM-DD or 'unknown'.

    Pass-through for already-formatted ISO dates; defensive for
    empty/unknown strings.
    """
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

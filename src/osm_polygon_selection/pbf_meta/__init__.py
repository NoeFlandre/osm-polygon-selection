"""PBF metadata: country -> Geofabrik URL, raw-dir conventions, date lookup.

Modules:
  sources  - NON_EUROPE_COUNTRIES map (country -> Geofabrik continent)
  regions  - sub-region / US-state slug handling
  downloads - geofabrik_url, format_pbf_date, pbf_date_for
"""

from osm_polygon_selection.pbf_meta.downloads import (
    DEFAULT_RAW_DIR,
    format_pbf_date,
    geofabrik_url,
    pbf_date_for,
)
from osm_polygon_selection.pbf_meta.sources import NON_EUROPE_COUNTRIES
from osm_polygon_selection.pbf_meta.regions import US_GEOFABRIK_REGIONS

__all__ = [
    "DEFAULT_RAW_DIR",
    "NON_EUROPE_COUNTRIES",
    "US_GEOFABRIK_REGIONS",
    "format_pbf_date",
    "geofabrik_url",
    "pbf_date_for",
]

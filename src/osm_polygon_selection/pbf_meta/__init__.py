"""PBF metadata: country -> Geofabrik URL, raw-dir conventions, date lookup.

Modules:
  sources    - NON_EUROPE_COUNTRIES map (country -> Geofabrik continent)
  regions    - sub-region / US-state slug handling
  regional   - canonical regional sub-PBF map (single source of truth)
  downloads  - geofabrik_url, format_pbf_date, pbf_date_for
"""

from osm_polygon_selection.pbf_meta.downloads import (
    DEFAULT_RAW_DIR,
    format_pbf_date,
    geofabrik_url,
    pbf_date_for,
)
from osm_polygon_selection.pbf_meta.regional import (
    ALL_REGIONAL_CANONICAL,
    REGIONAL_SUB_PBFS_CANONICAL,
)
from osm_polygon_selection.pbf_meta.regions import US_GEOFABRIK_REGIONS
from osm_polygon_selection.pbf_meta.sources import NON_EUROPE_COUNTRIES

__all__ = [
    "ALL_REGIONAL_CANONICAL",
    "DEFAULT_RAW_DIR",
    "NON_EUROPE_COUNTRIES",
    "REGIONAL_SUB_PBFS_CANONICAL",
    "US_GEOFABRIK_REGIONS",
    "format_pbf_date",
    "geofabrik_url",
    "pbf_date_for",
]

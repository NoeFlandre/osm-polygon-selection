"""Sub-region slug handling for countries that need to be split.

Some large countries (Brazil, China, India, Indonesia, Japan,
Canada, Russia, US) are processed as sub-regions to keep PBFs
manageable. The slug convention is ``<country>-<region>`` and
the URL nesting is country-specific.
"""

from __future__ import annotations

# Geofabrik's own US sub-regions (midwest / northeast / pacific /
# south / west) live as flat /north-america/us-<region>-latest.osm.pbf
# files, NOT under /us/<state>/. We must not treat these as state
# slugs and accidentally nest them.
US_GEOFABRIK_REGIONS = {"midwest", "northeast", "pacific", "south", "west"}

# Countries whose sub-PBFs nest directly under the country directory
# (e.g. /asia/india/central-zone/, /south-america/brazil/norte/).
SUB_REGION_PARENTS = {
    "brazil",
    "china",
    "india",
    "indonesia",
    "japan",
    "canada",
}

__all__ = ["SUB_REGION_PARENTS", "US_GEOFABRIK_REGIONS"]

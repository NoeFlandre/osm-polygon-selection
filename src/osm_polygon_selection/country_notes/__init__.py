"""Curated country notes + regional sub-PBF lists.

Used by organize_dataset.py to render the per-country READMEs.

The regional map is sourced from regional_pbf_meta (the canonical
single source of truth). Both this package and
:mod:`osm_polygon_selection.dataset_build.countries` derive from it,
so the build skip-list and the README regional list cannot drift.

Modules:
  data    - COUNTRY_NOTES dict + REGIONAL_SUB_PBFS list
  notes   - country_note, country_source_description
"""

from osm_polygon_selection.country_notes.data import (
    COUNTRY_NOTES,
    REGIONAL_SUB_PBFS,
)
from osm_polygon_selection.country_notes.notes import (
    country_note,
    country_source_description,
)
# Re-export so consumers don't reach into regional_pbf_meta directly.
from osm_polygon_selection.regional_pbf_meta import (  # noqa: F401
    REGIONAL_SUB_PBFS_CANONICAL,
)

__all__ = [
    "COUNTRY_NOTES",
    "REGIONAL_SUB_PBFS",
    "REGIONAL_SUB_PBFS_CANONICAL",
    "country_note",
    "country_source_description",
]

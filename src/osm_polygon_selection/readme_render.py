"""Backwards-compatible facade for the README renderers.

The actual implementations live in ``osm_polygon_selection.readme``
(one module per renderer, plus templates for the long strings).
This module re-exports the public names so existing call sites
(e.g. ``scripts/organize_dataset.py``) keep working without
import-path changes.

New code should import from ``osm_polygon_selection.readme``
directly.
"""

from __future__ import annotations

from osm_polygon_selection.country_notes import COUNTRY_NOTES  # noqa: F401
from osm_polygon_selection.readme import (  # noqa: F401
    PIPELINE_VERSION_DEFAULT,
    build_country_readme,
    build_folder_readme,
    build_root_readme,
    country_note,
    render_dataset_readme,
    write_metadata_yaml,
    write_readme,
)

# Legacy alias: pre-split callers may still reference this private
# helper. Delegates straight to the package's notes adapter.
_country_note = country_note

__all__ = [
    "COUNTRY_NOTES",
    "PIPELINE_VERSION_DEFAULT",
    "build_country_readme",
    "build_folder_readme",
    "build_root_readme",
    "country_note",
    "render_dataset_readme",
    "write_metadata_yaml",
    "write_readme",
]

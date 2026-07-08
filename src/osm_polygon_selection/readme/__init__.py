"""Public README rendering package.

Layout (one module per renderer, plus templates for long strings):

- ``dataset`` — the build_dataset pre-organize root README.
- ``root`` — the organize_dataset post-organize root README.
- ``folder`` — subfolder READMEs (``per_country/`` etc.).
- ``country`` — per-country READMEs.
- ``metadata`` — HF ``metadata.yaml`` sidecar.
- ``notes`` — country-note adapter around ``country_notes``.
- ``templates`` — long-form markdown / YAML template strings.

``osm_polygon_selection.readme_render`` remains a thin facade
importing the names here for backwards compatibility.
"""

from osm_polygon_selection.readme.country import build_country_readme
from osm_polygon_selection.readme.dataset import (
    render_dataset_readme,
    write_readme,
)
from osm_polygon_selection.readme.folder import build_folder_readme
from osm_polygon_selection.readme.metadata import write_metadata_yaml
from osm_polygon_selection.readme.notes import country_note
from osm_polygon_selection.readme.root import (
    PIPELINE_VERSION_DEFAULT,
    build_root_readme,
)

__all__ = [
    "PIPELINE_VERSION_DEFAULT",
    "build_country_readme",
    "build_folder_readme",
    "build_root_readme",
    "country_note",
    "render_dataset_readme",
    "write_metadata_yaml",
    "write_readme",
]

"""Public API for the dataset_organize pipeline.

Layout:
- :mod:`.manifests` — manifest read / update helpers
- :mod:`.readmes` — README writers (delegating to ``osm_polygon_selection.readme``)
- :mod:`.runner` — orchestration
"""

from osm_polygon_selection.dataset_organize.manifests import (
    load_manifest,
    maybe_load_split_counts,
    status_line,
)
from osm_polygon_selection.dataset_organize.readmes import (
    update_root_readme,
    write_country_readmes,
    write_folder_readmes,
)
from osm_polygon_selection.dataset_organize.runner import (
    DEFAULT_PREVIEW_SRC,
    DEFAULT_ROOT,
    DEFAULT_SAMPLE_SRC,
    run_organize,
)

__all__ = [
    "DEFAULT_PREVIEW_SRC",
    "DEFAULT_ROOT",
    "DEFAULT_SAMPLE_SRC",
    "load_manifest",
    "maybe_load_split_counts",
    "run_organize",
    "status_line",
    "update_root_readme",
    "write_country_readmes",
    "write_folder_readmes",
]

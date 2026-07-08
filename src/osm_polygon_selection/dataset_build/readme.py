"""Thin adapter that re-exports the build_dataset root README renderer.

The actual implementation lives in
``osm_polygon_selection.readme.dataset`` (split out from this
module during the readme/ package split). This module stays for
import backwards-compatibility with downstream tests and
scripts.
"""

from __future__ import annotations

from osm_polygon_selection.readme.dataset import (  # noqa: F401
    render_dataset_readme,
    write_readme,
)

"""HuggingFace dataset-viewer metadata sidecar writer.

Writes ``metadata.yaml`` to the dataset root. The YAML is
duplicated from the README frontmatter for HF compatibility
(so the metadata is visible even before the README is parsed).
"""

from __future__ import annotations

from pathlib import Path

from osm_polygon_selection.readme.templates import METADATA_YAML


def write_metadata_yaml(out_dir: Path) -> None:
    """Write HF's required metadata sidecar at ``out_dir/metadata.yaml``."""
    (out_dir / "metadata.yaml").write_text(METADATA_YAML)

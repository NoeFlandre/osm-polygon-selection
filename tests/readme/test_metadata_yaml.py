"""Tests for TestWriteMetadataYaml in osm_polygon_selection.readme_render.

Split from test_render.py during the quality-uplift-public-hardening phase.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from osm_polygon_selection.readme_render import write_metadata_yaml

class TestWriteMetadataYaml:
    def test_writes_yaml_with_required_fields(self, tmp_path: Path) -> None:
        write_metadata_yaml(tmp_path)
        path = tmp_path / "metadata.yaml"
        assert path.is_file()
        content = path.read_text()
        assert "license: odbl" in content
        assert "task_categories:" in content
        assert "size_categories:" in content

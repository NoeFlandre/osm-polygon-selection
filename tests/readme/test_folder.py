"""Tests for TestBuildFolderReadme in osm_polygon_selection.readme_render.

Split from test_render.py during the quality-uplift-public-hardening phase.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from .conftest import _country, _manifest
from osm_polygon_selection.readme_render import build_folder_readme

class TestBuildFolderReadme:
    @pytest.mark.parametrize("folder,expected_phrase", [
        ("per_country", "one folder per country"),
        ("combined", "all_world.parquet"),
        ("sample", "sample_map.jsonl"),
        ("preview", "map_preview.png"),
    ])
    def test_folder_readme_mentions_contents(
        self, folder: str, expected_phrase: str
    ) -> None:
        out = build_folder_readme(folder, n_countries=3)
        assert expected_phrase in out.lower()

    def test_unknown_folder_raises(self) -> None:
        with pytest.raises(ValueError):
            build_folder_readme("nonexistent", n_countries=1)



"""Tests for TestPipelineVersionDefault in osm_polygon_selection.readme_render.

Split from test_render.py during the quality-uplift-public-hardening phase.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from osm_polygon_selection.readme_render import PIPELINE_VERSION_DEFAULT

class TestPipelineVersionDefault:
    def test_is_v0_1_0(self) -> None:
        assert PIPELINE_VERSION_DEFAULT == "v0.1.0"



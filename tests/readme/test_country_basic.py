"""Basic country-readme shape tests (split from test_country.py).

Pins: returns string, mentions country + polygon count + extract status,
Geofabrik URL, and uses a country note.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from osm_polygon_selection.readme_render import build_country_readme

from .conftest import _country, _manifest


class TestBuildCountryReadmeBasic:
    def test_returns_string(self) -> None:
        out = build_country_readme(
            country="albania",
            n_polygons=14738,
            extract_status="clean",
            pbf_date="2026-06-26",
        )
        assert isinstance(out, str)

    def test_mentions_country_name(self) -> None:
        out = build_country_readme("albania", 100, "clean", "2026-06-26")
        assert "albania" in out.lower()

    def test_mentions_polygon_count(self) -> None:
        out = build_country_readme("albania", 1234, "clean", "2026-06-26")
        assert "1,234" in out or "1234" in out

    def test_mentions_extract_status(self) -> None:
        out = build_country_readme("albania", 100, "clean", "2026-06-26")
        assert "clean" in out

    def test_includes_geofabrik_url(self) -> None:
        out = build_country_readme("albania", 100, "clean", "2026-06-26")
        assert "download.geofabrik.de/europe/albania" in out

    def test_uses_country_note(self) -> None:
        out = build_country_readme("monaco", 2, "clean", "2026-06-26")
        assert "smallest" in out.lower() or "2 polygons" in out

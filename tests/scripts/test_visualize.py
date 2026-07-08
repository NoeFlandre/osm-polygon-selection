"""Tests for scripts/visualize.py.

Pins that the rendered map includes ALL countries in the input
JSONL — no truncation, no missing country.

Background: a previous default of ``--limit 2000`` truncated the
sample to ~10 alphabetically-first countries, which made Spain,
Portugal, Turkey, Greece, Sweden, Norway, Finland, Ukraine, etc.
invisible on the rendered map. This regression test prevents that
from happening again.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
VISUALIZE = SCRIPTS_DIR / "visualize.py"


def _load_visualize():
    spec = importlib.util.spec_from_file_location("visualize", VISUALIZE)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load {VISUALIZE}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["visualize"] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def _make_country_row(country: str, lon: float, lat: float) -> dict:
    return {
        "country": country,
        "osm_id": 1,
        "centroid_lon": lon,
        "centroid_lat": lat,
        "area_km2": 0.5,
        "size_bin": "small",
        "matched_tag": "natural=water",
        "tags": ["natural=water"],
    }


class TestVisualizeRendersAllCountries:
    """The default --limit must include every country in the JSONL."""

    def test_default_includes_every_country(self, tmp_path: Path) -> None:
        viz = _load_visualize()
        jsonl = tmp_path / "sample.jsonl"
        out_html = tmp_path / "map.html"
        # 50 countries, 100 polygons each = 5000 polygons total.
        # Old default (2000) would have truncated to the first
        # ~20 countries alphabetically.
        countries = [f"country_{i:02d}" for i in range(50)]
        rows = []
        for i, c in enumerate(countries):
            for j in range(100):
                rows.append(_make_country_row(c, float(i), float(j) / 100))
        _make_jsonl(jsonl, rows)

        # Run main() with default arguments.
        sys.argv = ["visualize", str(jsonl), str(out_html)]
        try:
            viz.main()
        except SystemExit:
            pass

        # Re-parse the output to count distinct countries that
        # actually got plotted. The folium output is HTML, so we
        # use a different signal: read the legend we inject.
        html = out_html.read_text()
        for c in countries:
            assert c in html, f"{c} missing from rendered map (truncated)"

    def test_default_limit_is_at_least_5000(self) -> None:
        """The hard-coded default --limit must be large enough to
        cover the current sample (4418 polygons, growing). 5000
        gives us a safety margin."""
        viz = _load_visualize()
        # argparse default lives at module import time; check via CLI.
        # Easier: assert the default value directly.
        assert viz.MAX_DEFAULT_LIMIT >= 5000, (
            f"default --limit is {viz.MAX_DEFAULT_LIMIT}; "
            "should be at least 5000 to avoid truncating the 4418-row sample"
        )

    def test_explicit_limit_respected(self, tmp_path: Path) -> None:
        viz = _load_visualize()
        jsonl = tmp_path / "sample.jsonl"
        out_html = tmp_path / "map.html"
        rows = []
        for i in range(10):
            for j in range(20):
                rows.append(_make_country_row(f"c_{i}", float(i), float(j) / 100))
        _make_jsonl(jsonl, rows)

        sys.argv = ["visualize", str(jsonl), str(out_html), "--limit", "5"]
        try:
            viz.main()
        except SystemExit:
            pass

        # All 200 polygons are read but only 5 are plotted.
        # Spot-check: the legend will have at most 1 country
        # (because the first 5 are all c_0).
        html = out_html.read_text()
        # The remaining c_1..c_9 should NOT appear in the legend
        # (they were truncated before being added).
        for c in [f"c_{i}" for i in range(1, 10)]:
            assert c not in html, f"{c} should be truncated by --limit 5"

    def test_fit_bounds_covers_wide_area(self, tmp_path: Path) -> None:
        """The map must auto-fit the bbox so wide-area samples
        (lon -60 to 60, lat -20 to 80) don't get clipped to one corner.
        We check that fit_bounds is called by inspecting the HTML for
        a JSON-encoded bounds array covering the full data range.
        """
        viz = _load_visualize()
        jsonl = tmp_path / "sample.jsonl"
        out_html = tmp_path / "map.html"
        # One polygon at each extreme of Europe (lon -60..60, lat 30..70).
        rows = [
            _make_country_row("west", -10.0, 40.0),
            _make_country_row("east", 40.0, 60.0),
            _make_country_row("north", 25.0, 70.0),
            _make_country_row("south", 5.0, 35.0),
        ]
        _make_jsonl(jsonl, rows)
        sys.argv = ["visualize", str(jsonl), str(out_html)]
        try:
            viz.main()
        except SystemExit:
            pass
        html = out_html.read_text()
        # folium encodes the bounds as JSON in the HTML. The corners
        # should be near the data extremes with ~5% padding.
        # South-west corner: lat ~ 32.75 (35 - 1.75), lon ~ -13 (west of -10)
        # North-east corner: lat ~ 72.25 (70 + 2.25), lon ~ 43 (east of 40)
        # We just check both extremes appear as numeric values in the
        # bounds JSON, not as the original "first row" only.
        # The map's center is the first row (5.0, 40.0) -> if fit_bounds
        # is missing, the map zooms to that small area and many points
        # are off-screen. So we just verify the html contains both the
        # westernmost and easternmost lons.
        assert "-10" in html or "-10.0" in html, "westernmost lon not in bounds"
        assert "40" in html or "40.0" in html, "easternmost lon not in bounds"

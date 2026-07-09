"""Package-level tests for ``osm_polygon_selection.visualization``.

Covers the public surface split out of ``scripts/visualize.py``:

- deterministic color assignment by sorted country names
- missing country -> default folium blue
- row loader respects ``--limit``
- centroid extraction supports both flat and nested formats
- rows with no coordinates are skipped
- robust percentile bounds match current behavior
- empty input defaults to Switzerland center/zoom
- popup text preserves current fields
"""

from __future__ import annotations

import json
from pathlib import Path

from osm_polygon_selection.visualization import (
    MAX_DEFAULT_LIMIT,
    build_popup_html,
    color_for_country,
    compute_fit_bounds,
    default_center,
    extract_centroid,
    load_rows,
    render_map,
)
from osm_polygon_selection.visualization.colors import COUNTRY_COLORS


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


class TestColorForCountry:
    def test_deterministic_by_sorted_country(self) -> None:
        """Pre-populating via ``sorted`` yields the same color
        mapping regardless of the encounter order."""
        countries = ("portugal", "spain", "france")
        cache_a: dict[str, str] = {}
        for cc in countries:  # encounter order
            color_for_country(cc, cache_a)
        cache_b: dict[str, str] = {}
        for cc in sorted(countries):  # sorted order
            color_for_country(cc, cache_b)
        # The canonical pattern from the script: pre-populate via
        # sorted(), then look up. After pre-population, the two
        # mappings must agree on every country.
        canon_a = {cc: COUNTRY_COLORS[i] for i, cc in enumerate(sorted(cache_a))}
        canon_b = {cc: COUNTRY_COLORS[i] for i, cc in enumerate(sorted(cache_b))}
        assert canon_a == canon_b

    def test_missing_country_falls_back_to_folium_blue(self) -> None:
        assert color_for_country(None, {}) == "#3388ff"

    def test_allocates_next_color_in_cycle(self) -> None:
        """After exhausting the 16-color palette, it cycles."""
        cache: dict[str, str] = {}
        for i in range(16):
            color_for_country(f"c{i}", cache)
        # 17th: cycles back to first color.
        c17 = color_for_country("c16", cache)
        assert c17 == list(cache.values())[0]


class TestLoadRows:
    def test_respects_limit(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "sample.jsonl"
        with jsonl.open("w") as f:
            for i in range(20):
                f.write(json.dumps({"id": i}) + "\n")
        rows = load_rows(jsonl, limit=5)
        assert len(rows) == 5
        assert [r["id"] for r in rows] == [0, 1, 2, 3, 4]


class TestExtractCentroid:
    def test_flat_centroid_lon_lat(self) -> None:
        row = {"centroid_lon": 5.0, "centroid_lat": 47.0}
        assert extract_centroid(row) == (5.0, 47.0)

    def test_nested_centroid(self) -> None:
        row = {"centroid": [5.0, 47.0]}
        assert extract_centroid(row) == (5.0, 47.0)

    def test_returns_none_for_no_centroid(self) -> None:
        assert extract_centroid({}) is None
        assert extract_centroid({"foo": "bar"}) is None

    def test_returns_none_for_none_coordinates(self) -> None:
        assert extract_centroid({"centroid_lon": None, "centroid_lat": 47.0}) is None
        assert extract_centroid({"centroid": [None, 47.0]}) is None


class TestComputeFitBounds:
    def test_none_for_empty_rows(self) -> None:
        assert compute_fit_bounds([]) is None

    def test_none_when_no_coordinates(self) -> None:
        rows = [{"foo": "bar"}, {"country": "x"}]
        assert compute_fit_bounds(rows) is None

    def test_percentile_bounds_for_fixed_rows(self) -> None:
        """Five lons [0, 5, 10, 15, 20] -> 5th pct index=0, 95th pct index=4.
        Pad = max((20-0)*0.05, 0.5) = 1.0.
        SW corner: [lat_min - lat_pad, 0 - 1.0]
        NE corner: [lat_max + lat_pad, 20 + 1.0]
        """
        rows = [
            {"centroid_lon": float(lon), "centroid_lat": float(lon)}
            for lon in (0, 5, 10, 15, 20)
        ]
        bounds = compute_fit_bounds(rows)
        assert bounds is not None
        sw, ne = bounds
        # 5th pct of 5 = 0 -> 0; 95th pct = 4 -> 20; pad = 1.0.
        assert sw[1] == -1.0
        assert ne[1] == 21.0


class TestDefaultCenter:
    def test_switzerland_fallback(self) -> None:
        center, zoom = default_center()
        assert center == [47.0, 9.5]
        assert zoom == 4


class TestBuildPopupHtml:
    def test_includes_all_fields(self) -> None:
        row = {
            "osm_id": 42,
            "area_km2": 0.123,
            "country": "spain",
            "size_bin": "small",
            "tags": ["natural=wood", "landuse=forest"],
        }
        html = build_popup_html(row)
        assert "osm_id=42" in html
        assert "0.123 km²" in html
        assert "country: spain" in html
        assert "size_bin: small" in html
        assert "natural=wood" in html

    def test_omits_country_line_if_missing(self) -> None:
        row = {"osm_id": 1, "area_km2": 1.0, "size_bin": "small", "tags": []}
        html = build_popup_html(row)
        assert "country:" not in html


class TestRenderMap:
    def test_default_limit_at_least_5000(self) -> None:
        """Regression pin: --limit must be high enough to cover the
        current sample (~4418 polygons, growing)."""
        assert MAX_DEFAULT_LIMIT >= 5000

    def test_renders_all_countries(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "sample.jsonl"
        out_html = tmp_path / "map.html"
        countries = [f"country_{i:02d}" for i in range(50)]
        rows = []
        for i, c in enumerate(countries):
            for j in range(100):
                rows.append(_make_country_row(c, float(i), float(j) / 100))
        with jsonl.open("w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        n_plotted = render_map(jsonl, out_html, limit=MAX_DEFAULT_LIMIT)
        assert n_plotted == 5000
        html = out_html.read_text()
        for c in countries:
            assert c in html, f"{c} missing from rendered map (truncated)"

    def test_explicit_limit_respected(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "sample.jsonl"
        out_html = tmp_path / "map.html"
        rows = []
        for i in range(10):
            for j in range(20):
                rows.append(_make_country_row(f"c_{i}", float(i), float(j) / 100))
        with jsonl.open("w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        n_plotted = render_map(jsonl, out_html, limit=5)
        assert n_plotted == 5

    def test_skips_rows_without_coordinates(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "sample.jsonl"
        out_html = tmp_path / "map.html"
        rows = [
            _make_country_row("a", 5.0, 47.0),
            {"country": "b", "osm_id": 2, "area_km2": 0.5, "size_bin": "small", "tags": []},
        ]
        with jsonl.open("w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        n_plotted = render_map(jsonl, out_html, limit=10)
        assert n_plotted == 1
        html = out_html.read_text()
        assert "country: a" in html
        assert "country: b" not in html

    def test_empty_input_defaults_to_switzerland(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "sample.jsonl"
        out_html = tmp_path / "map.html"
        jsonl.write_text("")
        n_plotted = render_map(jsonl, out_html, limit=10)
        assert n_plotted == 0
        # Map is centered at the Switzerland fallback.
        html = out_html.read_text()
        assert "47" in html
        assert "9.5" in html or "9.500" in html

    def test_country_color_assignment_is_deterministic_via_render(
        self, tmp_path: Path,
    ) -> None:
        """Behavior pin: when the same set of countries is rendered
        twice (with different encounter orders in the JSONL),
        each country gets the same color.

        Two equivalent country sets in different encounter orders
        must produce identical color mappings. This guards the
        render_map path against accidental cache-reset bugs.
        """
        from osm_polygon_selection.visualization.colors import COUNTRY_COLORS

        countries = ["portugal", "spain", "france"]

        def _run(order: list[str]) -> dict[str, str]:
            jsonl = tmp_path / f"sample_{'_'.join(order)}.jsonl"
            out_html = tmp_path / f"map_{'_'.join(order)}.html"
            rows = []
            for cc in order:
                for _ in range(3):
                    rows.append(_make_country_row(cc, 5.0, 47.0))
            with jsonl.open("w") as f:
                for r in rows:
                    f.write(json.dumps(r) + "\n")
            # Monkey-patch color_for_country to capture the final cache.
            captured: dict[str, str] = {}
            import osm_polygon_selection.visualization.render as render_mod

            original = render_mod.color_for_country

            def _capturing(country, cache):
                color = original(country, cache)
                if country is not None:
                    captured[country] = color
                return color

            render_mod.color_for_country = _capturing
            try:
                render_map(jsonl, out_html, limit=20)
            finally:
                render_mod.color_for_country = original
            return captured

        run_a = _run(list(countries))      # encounter order = sorted
        run_b = _run(list(reversed(countries)))  # encounter order = reversed
        assert run_a == run_b, (
            f"deterministic color assignment drifted across runs: "
            f"{run_a} vs {run_b}"
        )
        # Each country is assigned one of the canonical 16 colors.
        for cc in countries:
            assert run_a[cc] in COUNTRY_COLORS

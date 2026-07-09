"""Tests for osm_polygon_selection.country_table.

TDD red phase: written before src/osm_polygon_selection/country_table.py.

The canonical home is :mod:`osm_polygon_selection.readme.tables`; the
root-level module is a backwards-compat facade.
"""

from __future__ import annotations

from osm_polygon_selection.country_table import build_country_table
from osm_polygon_selection.readme.tables import build_country_table as build_country_table_canonical


def _country(name: str, n: int, status: str = "clean") -> dict:
    return {"country": name, "n_polygons": n, "extract_status": status}


def test_canonical_and_facade_produce_identical_output() -> None:
    """The canonical module and the root facade must agree."""
    countries = [_country("albania", 1000), _country("france", 5000)]
    assert build_country_table(countries) == build_country_table_canonical(countries)


class TestBuildCountryTable:
    def test_returns_string(self) -> None:
        out = build_country_table([_country("albania", 100)])
        assert isinstance(out, str)

    def test_header_has_columns(self) -> None:
        out = build_country_table([_country("albania", 100)])
        assert "| Country | Polygons | Status |" in out
        assert "|---------|----------|--------|" in out

    def test_polygons_formatted_with_thousands_separator(self) -> None:
        out = build_country_table([_country("germany", 1131888)])
        assert "1,131,888" in out

    def test_rows_sorted_alphabetically(self) -> None:
        countries = [_country("zimbabwe", 1), _country("albania", 2)]
        out = build_country_table(countries)
        assert out.index("albania") < out.index("zimbabwe")

    def test_killed_country_still_appears(self) -> None:
        out = build_country_table([_country("italy", 1000, status="killed")])
        assert "italy" in out
        assert "killed" in out

    def test_status_column_present(self) -> None:
        out = build_country_table([_country("albania", 100)])
        assert "clean" in out

    def test_grand_total_row_appended(self) -> None:
        out = build_country_table([_country("albania", 100), _country("italy", 50)])
        assert "**Total**" in out
        assert "150" in out

    def test_total_equals_sum(self) -> None:
        out = build_country_table([_country("a", 100), _country("b", 200), _country("c", 300)])
        assert "600" in out

    def test_empty_input_returns_non_empty_table(self) -> None:
        out = build_country_table([])
        assert "Country" in out  # header still present
        assert "Total" in out  # 0 total row

    def test_no_trailing_clean_paren(self) -> None:
        """Old bullet format had '(clean)' after the polygons count; gone now."""
        out = build_country_table([_country("albania", 100)])
        assert "(clean)" not in out.split("**Total**")[0]

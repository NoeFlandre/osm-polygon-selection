"""Tests for the README per-country summary table builder.

The `build_country_table` function takes the same `countries_done`
list-of-dicts that's already produced by `scripts/build_dataset.py`
(`{"country": str, "n_polygons": int, "extract_status": str, ...}`)
and renders a markdown table suitable for the `## Per-country summary`
section of the published dataset README.

These tests pin the table format so future refactors don't drift.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

BUILD_DATASET = Path(__file__).resolve().parents[2] / "scripts" / "build_dataset.py"
spec = importlib.util.spec_from_file_location("build_dataset", BUILD_DATASET)
if spec is None or spec.loader is None:
    raise ImportError(f"could not load {BUILD_DATASET}")
build_dataset = importlib.util.module_from_spec(spec)
sys.modules["build_dataset"] = build_dataset
spec.loader.exec_module(build_dataset)


# --- helpers ---------------------------------------------------------------


def _lines(table: str) -> list[str]:
    """Split a markdown table into non-empty lines."""
    return [ln for ln in table.splitlines() if ln.strip()]


def _data_rows(table: str) -> list[list[str]]:
    """Return just the data rows of a markdown table (skip header + sep)."""
    rows = _lines(table)
    # First line is the header, second line is the `|---|...|` separator.
    assert len(rows) >= 2, f"table too short:\n{table}"
    return [_split(r) for r in rows[2:]]


def _split(row: str) -> list[str]:
    """Split a `| a | b | c |` row into cells."""
    return [c.strip() for c in row.strip().strip("|").split("|")]


# --- tests -----------------------------------------------------------------


class TestBuildCountryTable:
    """The per-country summary should be a markdown table."""

    def test_returns_string(self):
        countries = [{"country": "albania", "n_polygons": 14738, "extract_status": "clean"}]
        out = build_dataset.build_country_table(countries)
        assert isinstance(out, str)
        assert out  # not empty

    def test_header_row_has_expected_columns(self):
        out = build_dataset.build_country_table(
            [{"country": "albania", "n_polygons": 14738, "extract_status": "clean"}]
        )
        header = _split(_lines(out)[0])
        assert header == ["Country", "Polygons", "Status"]

    def test_separator_row_present(self):
        out = build_dataset.build_country_table(
            [{"country": "albania", "n_polygons": 14738, "extract_status": "clean"}]
        )
        sep = _lines(out)[1]
        # Standard markdown separator: `|---|---|---|`
        cells = _split(sep)
        assert len(cells) == 3
        assert all(set(c) <= {"-"} for c in cells), f"bad separator: {sep!r}"

    def test_polygons_formatted_with_thousands_separator(self):
        out = build_dataset.build_country_table(
            [
                {"country": "germany", "n_polygons": 1131888, "extract_status": "clean"},
                {"country": "albania", "n_polygons": 14738, "extract_status": "clean"},
            ]
        )
        rows = _data_rows(out)
        # Find germany row regardless of order
        germany_row = next(r for r in rows if r[0] == "germany")
        albania_row = next(r for r in rows if r[0] == "albania")
        assert germany_row[1] == "1,131,888"
        assert albania_row[1] == "14,738"

    def test_rows_sorted_alphabetically_by_country(self):
        countries = [
            {"country": "zimbabwe", "n_polygons": 1, "extract_status": "clean"},
            {"country": "albania", "n_polygons": 2, "extract_status": "clean"},
            {"country": "mexico", "n_polygons": 3, "extract_status": "clean"},
        ]
        out = build_dataset.build_country_table(countries)
        rows = _data_rows(out)
        # Last row is the Total row; skip it for the sort check.
        data_rows = [r for r in rows if not r[0].startswith("**")]
        country_names = [r[0] for r in data_rows]
        assert country_names == ["albania", "mexico", "zimbabwe"]

    def test_killed_country_still_appears(self):
        """A country with extract_status='killed' must not be filtered out."""
        out = build_dataset.build_country_table(
            [
                {"country": "albania", "n_polygons": 14, "extract_status": "clean"},
                {"country": "france", "n_polygons": 0, "extract_status": "killed"},
            ]
        )
        country_names = [r[0] for r in _data_rows(out)]
        assert "france" in country_names
        france_row = next(r for r in _data_rows(out) if r[0] == "france")
        assert france_row[2] == "killed"

    def test_status_column_present(self):
        out = build_dataset.build_country_table(
            [{"country": "albania", "n_polygons": 100, "extract_status": "clean"}]
        )
        rows = _data_rows(out)
        # First row is the country; second is the Total row.
        assert rows[0][2] == "clean"
        assert rows[-1][0] == "**Total**"

    def test_grand_total_row_appended(self):
        countries = [
            {"country": "albania", "n_polygons": 1000, "extract_status": "clean"},
            {"country": "france", "n_polygons": 5000, "extract_status": "clean"},
            {"country": "germany", "n_polygons": 2500, "extract_status": "clean"},
        ]
        out = build_dataset.build_country_table(countries)
        rows = _data_rows(out)
        # The last row should be the Total row.
        total_row = rows[-1]
        assert total_row[0] == "**Total**"
        assert total_row[1] == "8,500"
        # Status column for the total can be empty or "—" but not "clean".
        assert total_row[2] != "clean"

    def test_no_trailing_clean_paren_in_polygons_column(self):
        """The polygons cell should NOT contain '(clean)' or similar suffix."""
        out = build_dataset.build_country_table(
            [{"country": "albania", "n_polygons": 100, "extract_status": "clean"}]
        )
        rows = _data_rows(out)
        polygon_cells = [r[1] for r in rows]
        for cell in polygon_cells:
            # Thousands separator is OK; nothing else should appear.
            assert "clean" not in cell, f"unexpected 'clean' in polygons cell: {cell}"
            assert "(" not in cell and ")" not in cell, (
                f"unexpected parens in polygons cell: {cell}"
            )

    def test_total_equals_sum_of_polygons(self):
        countries = [
            {"country": "a", "n_polygons": 1, "extract_status": "clean"},
            {"country": "b", "n_polygons": 22, "extract_status": "clean"},
            {"country": "c", "n_polygons": 333, "extract_status": "killed"},
            {"country": "d", "n_polygons": 4444, "extract_status": "clean"},
        ]
        out = build_dataset.build_country_table(countries)
        total_row = _data_rows(out)[-1]
        assert total_row[1] == "4,800"

    def test_empty_input_returns_non_empty_table(self):
        """Even with no countries, the header is rendered and the Total row shows 0."""
        out = build_dataset.build_country_table([])
        assert out  # not empty
        lines = _lines(out)
        assert "Country" in lines[0]
        # The Total row still appears with a sum of 0.
        total_row = _data_rows(out)[-1]
        assert total_row[0] == "**Total**"
        assert total_row[1] == "0"


class TestBuildCountryTableIntegration:
    """Smoke test against the real data shape produced by the script."""

    def test_realistic_europe_shape(self):
        # Mimics the actual shape the script produces after sorting.
        countries = [
            {"country": "albania", "n_polygons": 14738, "extract_status": "clean", "pbf_date": "2026-06-27"},
            {"country": "andorra", "n_polygons": 776, "extract_status": "clean", "pbf_date": "2026-06-27"},
            {"country": "germany", "n_polygons": 1131888, "extract_status": "clean", "pbf_date": "2026-06-27"},
        ]
        out = build_dataset.build_country_table(countries)
        rows = _data_rows(out)
        assert len(rows) == 4  # 3 countries + total
        assert rows[0][0] == "albania"
        assert rows[1][0] == "andorra"
        assert rows[2][0] == "germany"
        assert rows[-1][0] == "**Total**"
        assert rows[-1][1] == "1,147,402"

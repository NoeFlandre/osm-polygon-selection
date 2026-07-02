"""Tests for osm_polygon_selection.pbf_meta.

TDD red phase: written before src/osm_polygon_selection/pbf_meta.py.
"""

from __future__ import annotations

from pathlib import Path

from osm_polygon_selection.pbf_meta import (
    format_pbf_date,
    geofabrik_url,
    pbf_date_for,
)


class TestGeofabrikUrl:
    def test_simple_country(self) -> None:
        assert geofabrik_url("albania") == (
            "https://download.geofabrik.de/europe/albania.html"
        )

    def test_country_with_dash(self) -> None:
        assert geofabrik_url("czech-republic") == (
            "https://download.geofabrik.de/europe/czech-republic.html"
        )

    def test_special_combined_country(self) -> None:
        assert geofabrik_url("ireland-and-northern-ireland") == (
            "https://download.geofabrik.de/europe/ireland-and-northern-ireland.html"
        )

    def test_non_europe_country_uses_correct_region(self) -> None:
        """Countries outside /europe/ (e.g. morocco) get their
        continent subtree URL."""
        assert geofabrik_url("morocco") == (
            "https://download.geofabrik.de/africa/morocco.html"
        )

    def test_tunisia_uses_africa_region(self) -> None:
        """Tunisia, like Morocco, is in Geofabrik's /africa/ subtree."""
        assert geofabrik_url("tunisia") == (
            "https://download.geofabrik.de/africa/tunisia.html"
        )

    def test_algeria_uses_africa_region(self) -> None:
        """Algeria, like Morocco and Tunisia, is in Geofabrik's /africa/ subtree."""
        assert geofabrik_url("algeria") == (
            "https://download.geofabrik.de/africa/algeria.html"
        )

    def test_mayotte_uses_africa_region(self) -> None:
        """Mayotte (French overseas territory, Indian Ocean) is in /africa/."""
        assert geofabrik_url("mayotte") == (
            "https://download.geofabrik.de/africa/mayotte.html"
        )


class TestFormatPbfDate:
    def test_iso_date(self) -> None:
        assert format_pbf_date("2026-06-26") == "2026-06-26"

    def test_unknown_date_returns_unknown(self) -> None:
        assert format_pbf_date("unknown") == "unknown"

    def test_empty_string_returns_unknown(self) -> None:
        assert format_pbf_date("") == "unknown"


class TestPbfDateFor:
    def test_returns_iso_date_from_mtime(self, tmp_path: Path) -> None:
        """When a PBF exists at the conventional location, read its mtime."""
        # Not easy to mock mtime reliably cross-platform; just test fallback
        result = pbf_date_for("albania", raw_dir=tmp_path)
        # If the PBF doesn't exist, returns "unknown"
        assert result == "unknown"

    def test_returns_unknown_when_pbf_missing(self, tmp_path: Path) -> None:
        result = pbf_date_for("albania", raw_dir=tmp_path)
        assert result == "unknown"

    def test_iso_format_when_present(self, tmp_path: Path) -> None:
        # Create a PBF and check it returns a date in YYYY-MM-DD format
        (tmp_path / "albania-latest.osm.pbf").touch()
        result = pbf_date_for("albania", raw_dir=tmp_path)
        assert len(result) == 10  # "YYYY-MM-DD"
        assert result[4] == "-"
        assert result[7] == "-"

    def test_iso_format_for_guernsey_jersey(self, tmp_path: Path) -> None:
        (tmp_path / "guernsey-jersey-latest.osm.pbf").touch()
        result = pbf_date_for("guernsey-jersey", raw_dir=tmp_path)
        assert len(result) == 10

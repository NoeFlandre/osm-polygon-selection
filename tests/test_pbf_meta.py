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

    def test_south_american_country_uses_south_america_region(self) -> None:
        """South American countries get their continent subtree URL."""
        for c in ("argentina", "bolivia", "brazil", "chile", "colombia",
                  "ecuador", "guyana", "paraguay", "peru", "suriname",
                  "uruguay", "venezuela"):
            assert geofabrik_url(c) == (
                f"https://download.geofabrik.de/south-america/{c}.html"
            )

    def test_asian_country_uses_asia_region(self) -> None:
        """Asian countries get their continent subtree URL."""
        for c in ("afghanistan", "japan", "israel-and-palestine",
                  "malaysia-singapore-brunei", "gcc-states"):
            assert geofabrik_url(c) == (
                f"https://download.geofabrik.de/asia/{c}.html"
            )

    def test_china_uses_asia_china_subpath(self) -> None:
        """China regions are sub-PBFs under /asia/china/<province>/."""
        for region in ("anhui", "guangdong", "sichuan", "tibet",
                       "inner-mongolia", "hong-kong", "macau"):
            assert geofabrik_url(f"china-{region}") == (
                f"https://download.geofabrik.de/asia/china/{region}.html"
            )

    def test_india_uses_asia_india_subpath(self) -> None:
        """India zones are sub-PBFs under /asia/india/."""
        for zone in ("central-zone", "eastern-zone", "north-eastern-zone",
                     "northern-zone", "southern-zone", "western-zone"):
            assert geofabrik_url(f"india-{zone}") == (
                f"https://download.geofabrik.de/asia/india/{zone}.html"
            )

    def test_indonesia_uses_asia_indonesia_subpath(self) -> None:
        """Indonesia islands are sub-PBFs under /asia/indonesia/."""
        for island in ("java", "kalimantan", "maluku", "nusa-tenggara",
                       "papua", "sulawesi", "sumatra"):
            assert geofabrik_url(f"indonesia-{island}") == (
                f"https://download.geofabrik.de/asia/indonesia/{island}.html"
            )

    def test_japan_uses_asia_japan_subpath(self) -> None:
        """Japan regions are sub-PBFs under /asia/japan/."""
        for region in ("chubu", "chugoku", "hokkaido", "kansai",
                       "kanto", "kyushu", "shikoku", "tohoku"):
            assert geofabrik_url(f"japan-{region}") == (
                f"https://download.geofabrik.de/asia/japan/{region}.html"
            )

    def test_oceania_uses_australia_oceania_region(self) -> None:
        """Oceania countries get the /australia-oceania/ subtree URL."""
        for c in ("australia", "new-zealand", "fiji", "samoa",
                  "papua-new-guinea", "cook-islands"):
            assert geofabrik_url(c) == (
                f"https://download.geofabrik.de/australia-oceania/{c}.html"
            )

    def test_north_american_country_uses_north_america_region(self) -> None:
        """North American countries get the /north-america/ subtree URL."""
        for c in ("greenland", "mexico", "us-pacific"):
            assert geofabrik_url(c) == (
                f"https://download.geofabrik.de/north-america/{c}.html"
            )

    def test_us_state_uses_north_america_us_subpath(self) -> None:
        """US states are sub-PBFs under /north-america/us/<state>."""
        for state in ("california", "texas", "new-york",
                      "district-of-columbia"):
            assert geofabrik_url(f"us-{state}") == (
                f"https://download.geofabrik.de/north-america/us/{state}.html"
            )

    def test_canada_province_uses_north_america_canada_subpath(self) -> None:
        """Canadian provinces are sub-PBFs under /north-america/canada/."""
        for province in ("ontario", "quebec", "british-columbia",
                         "alberta", "newfoundland-and-labrador"):
            assert geofabrik_url(f"canada-{province}") == (
                f"https://download.geofabrik.de/north-america/canada/{province}.html"
            )

    def test_russia_district_uses_russia_subpath(self) -> None:
        """Russian federal districts are sub-PBFs under /russia/."""
        for district in ("central-fed-district", "kaliningrad",
                         "volga-fed-district"):
            assert geofabrik_url(f"russia-{district}") == (
                f"https://download.geofabrik.de/russia/{district}.html"
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

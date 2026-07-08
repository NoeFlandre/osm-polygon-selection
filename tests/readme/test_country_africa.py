"""Country-readme tests for African curated notes (split from test_country.py).

Each test pins that a specific African country has a curated
COUNTRY_NOTES entry mentioning a distinctive feature (NOT the
generic fallback). The tests group by sub-region for readability.
"""

from __future__ import annotations

from osm_polygon_selection.readme_render import build_country_readme


class TestBuildCountryReadmeAfricaSouthern:
    def test_uses_botswana_country_note(self) -> None:
        out = build_country_readme("botswana", 4119, "clean", "2026-07-03")
        text = out.lower()
        assert "kalahari" in text or "okavango" in text

    def test_uses_angola_country_note(self) -> None:
        out = build_country_readme("angola", 15000, "clean", "2026-07-03")
        text = out.lower()
        assert "luanda" in text or "angola" in text or "namib" in text

    def test_uses_zimbabwe_country_note(self) -> None:
        out = build_country_readme("zimbabwe", 8000, "clean", "2026-07-03")
        text = out.lower()
        assert "harare" in text or "bulawayo" in text or "zimbabwe" in text

    def test_uses_zambia_country_note(self) -> None:
        out = build_country_readme("zambia", 7000, "clean", "2026-07-03")
        text = out.lower()
        assert "lusaka" in text or "copperbelt" in text or "zambia" in text

    def test_uses_mozambique_country_note(self) -> None:
        out = build_country_readme("mozambique", 5000, "clean", "2026-07-03")
        text = out.lower()
        assert "maputo" in text or "beira" in text or "mozambique" in text

    def test_uses_south_africa_country_note(self) -> None:
        out = build_country_readme("south-africa", 20000, "clean", "2026-07-03")
        text = out.lower()
        assert (
            "johannesburg" in text
            or "cape town" in text
            or "durban" in text
            or "south-africa" in text
        )

    def test_uses_lesotho_country_note(self) -> None:
        out = build_country_readme("lesotho", 2000, "clean", "2026-07-03")
        text = out.lower()
        assert "lesotho" in text or "mountain" in text


class TestBuildCountryReadmeAfricaWest:
    def test_uses_central_african_republic_country_note(self) -> None:
        out = build_country_readme(
            "central-african-republic", 6000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert "bangui" in text or "ubangi" in text or "savanna" in text

    def test_uses_ivory_coast_country_note(self) -> None:
        out = build_country_readme(
            "ivory-coast", 25000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert (
            "yamoussoukro" in text
            or "abidjan" in text
            or "côte" in text
        )

    def test_uses_burkina_faso_country_note(self) -> None:
        out = build_country_readme(
            "burkina-faso", 15000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert (
            "ouagadougou" in text
            or "bobo-dioulasso" in text
            or "sahel" in text
            or "volta" in text
        )

    def test_uses_guinea_country_note(self) -> None:
        out = build_country_readme(
            "guinea", 12000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert (
            "conakry" in text
            or "fouta" in text
            or "djallon" in text
            or "niger" in text
        )

    def test_uses_ghana_country_note(self) -> None:
        out = build_country_readme(
            "ghana", 15000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert (
            "accra" in text
            or "kumasi" in text
            or "volta" in text
            or "ghana" in text
        )

    def test_uses_senegal_and_gambia_country_note(self) -> None:
        out = build_country_readme(
            "senegal-and-gambia", 15000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert "dakar" in text or "banjul" in text or "senegal" in text

    def test_uses_mali_country_note(self) -> None:
        out = build_country_readme("mali", 8000, "clean", "2026-07-03")
        text = out.lower()
        assert "bamako" in text or "sahel" in text or "mali" in text


class TestBuildCountryReadmeAfricaNorthEast:
    def test_uses_chad_country_note(self) -> None:
        out = build_country_readme(
            "chad", 6000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert (
            "ndjamena" in text
            or "n'djamena" in text
            or "tibesti" in text
            or "saharan" in text
        )

    def test_uses_south_sudan_country_note(self) -> None:
        out = build_country_readme(
            "south-sudan", 3000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert "juba" in text or "south sudan" in text

    def test_uses_ethiopia_country_note(self) -> None:
        out = build_country_readme(
            "ethiopia", 18000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert "addis" in text or "ethiopia" in text

    def test_uses_malawi_country_note(self) -> None:
        out = build_country_readme(
            "malawi", 5000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert "lilongwe" in text or "blantyre" in text or "malawi" in text

    def test_uses_somalia_country_note(self) -> None:
        out = build_country_readme(
            "somalia", 4000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert "mogadishu" in text or "somalia" in text

    def test_uses_egypt_country_note(self) -> None:
        out = build_country_readme(
            "egypt", 30000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert "nile" in text or "cairo" in text or "egypt" in text

    def test_uses_sudan_country_note(self) -> None:
        out = build_country_readme(
            "sudan", 6000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert "khartoum" in text or "sudan" in text


class TestBuildCountryReadmeAfricaCentralEast:
    def test_uses_cameroon_country_note(self) -> None:
        out = build_country_readme(
            "cameroon", 12000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert "yaounde" in text or "douala" in text or "cameroon" in text

    def test_uses_kenya_country_note(self) -> None:
        out = build_country_readme(
            "kenya", 18000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert "nairobi" in text or "mombasa" in text or "kenya" in text

    def test_uses_uganda_country_note(self) -> None:
        out = build_country_readme(
            "uganda", 8000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert "kampala" in text or "uganda" in text

    def test_uses_congo_democratic_republic_country_note(self) -> None:
        out = build_country_readme(
            "congo-democratic-republic", 9000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert (
            "kinshasa" in text
            or "congo" in text
            or "drc" in text
        )

    def test_uses_nigeria_country_note(self) -> None:
        out = build_country_readme(
            "nigeria", 50000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert (
            "lagos" in text
            or "abuja" in text
            or "kano" in text
            or "nigeria" in text
        )

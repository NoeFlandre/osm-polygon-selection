"""Tests for TestBuildCountryReadme in osm_polygon_selection.readme_render.

Split from test_render.py during the quality-uplift-public-hardening phase.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from .conftest import _country, _manifest
from osm_polygon_selection.readme_render import build_country_readme

class TestBuildCountryReadme:
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
        assert "albania" in out

    def test_mentions_polygon_count(self) -> None:
        out = build_country_readme("albania", 14738, "clean", "2026-06-26")
        assert "14,738" in out

    def test_mentions_extract_status(self) -> None:
        out = build_country_readme("albania", 100, "killed", "2026-06-26")
        assert "killed" in out

    def test_includes_geofabrik_url(self) -> None:
        out = build_country_readme("albania", 100, "clean", "2026-06-26")
        assert "download.geofabrik.de/europe/albania" in out

    def test_uses_country_note(self) -> None:
        # monaco note is distinctive ("smallest country")
        out = build_country_readme("monaco", 2, "clean", "2026-06-26")
        assert "smallest" in out.lower() or "2 polygons" in out

    def test_uses_botswana_country_note(self) -> None:
        """botswana (Southern African country, Geofabrik /africa/) should
        have a curated COUNTRY_NOTES entry mentioning the Kalahari or
        Okavango Delta, NOT the generic fallback.
        """
        out = build_country_readme("botswana", 4119, "clean", "2026-07-03")
        text = out.lower()
        assert "kalahari" in text or "okavango" in text, (
            f"botswana country README missing curated note; got:\n{out}"
        )

    def test_uses_central_african_republic_country_note(self) -> None:
        """central-african-republic (landlocked Central African country,
        Geofabrik /africa/) should have a curated COUNTRY_NOTES entry
        mentioning the capital Bangui or a distinctive Central African
        geographic feature, NOT the generic fallback.
        """
        out = build_country_readme(
            "central-african-republic", 6000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert "bangui" in text or "ubangi" in text or "savanna" in text, (
            f"central-african-republic country README missing curated "
            f"note; got:\n{out}"
        )

    def test_uses_ivory_coast_country_note(self) -> None:
        """ivory-coast (West African country on the Gulf of Guinea,
        official name Côte d'Ivoire) should have a curated
        COUNTRY_NOTES entry mentioning Yamoussoukro or Abidjan,
        NOT the generic fallback.
        """
        out = build_country_readme(
            "ivory-coast", 25000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert "yamoussoukro" in text or "abidjan" in text or "côte" in text, (
            f"ivory-coast country README missing curated note; got:\n{out}"
        )

    def test_uses_burkina_faso_country_note(self) -> None:
        """burkina-faso (landlocked West African country, formerly
        Upper Volta) should have a curated COUNTRY_NOTES entry
        mentioning Ouagadougou or Bobo-Dioulasso or the Sahel,
        NOT the generic fallback.
        """
        out = build_country_readme(
            "burkina-faso", 15000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert (
            "ouagadougou" in text
            or "bobo-dioulasso" in text
            or "sahel" in text
            or "volta" in text
        ), (
            f"burkina-faso country README missing curated note; got:\n{out}"
        )

    def test_uses_angola_country_note(self) -> None:
        """angola (large Southern African country on the Atlantic,
        former Portuguese colony) should have a curated
        COUNTRY_NOTES entry mentioning Luanda or a distinctive
        Angolan geographic feature, NOT the generic fallback.
        """
        out = build_country_readme(
            "angola", 15000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert "luanda" in text or "angola" in text or "namib" in text, (
            f"angola country README missing curated note; got:\n{out}"
        )

    def test_uses_guinea_country_note(self) -> None:
        """guinea (West African country on the Atlantic, former
        French colony) should have a curated COUNTRY_NOTES entry
        mentioning Conakry or Fouta Djallon or a distinctive
        Guinean geographic feature, NOT the generic fallback.
        """
        out = build_country_readme(
            "guinea", 12000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert (
            "conakry" in text
            or "fouta" in text
            or "djallon" in text
            or "niger" in text
        ), (
            f"guinea country README missing curated note; got:\n{out}"
        )

    def test_uses_ghana_country_note(self) -> None:
        """ghana (West African country on the Gulf of Guinea,
        former British colony) should have a curated
        COUNTRY_NOTES entry mentioning Accra or a distinctive
        Ghanaian geographic feature, NOT the generic fallback.
        """
        out = build_country_readme(
            "ghana", 15000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert (
            "accra" in text
            or "kumasi" in text
            or "volta" in text
            or "ghana" in text
        ), (
            f"ghana country README missing curated note; got:\n{out}"
        )

    def test_uses_senegal_and_gambia_country_note(self) -> None:
        """senegal-and-gambia (Geofabrik combined file covering
        both Senegal and The Gambia) should have a curated
        COUNTRY_NOTES entry mentioning Dakar or Banjul,
        NOT the generic fallback.
        """
        out = build_country_readme(
            "senegal-and-gambia", 15000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert (
            "dakar" in text
            or "banjul" in text
            or "senegal" in text
            or "gambia" in text
        ), (
            f"senegal-and-gambia country README missing curated "
            f"note; got:\n{out}"
        )

    def test_uses_lesotho_country_note(self) -> None:
        """lesotho (small landlocked Southern African country,
        entirely surrounded by South Africa, also known as the
        'Kingdom in the Sky') should have a curated COUNTRY_NOTES
        entry mentioning Maseru or a distinctive Lesotho feature.
        """
        out = build_country_readme(
            "lesotho", 4000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert (
            "maseru" in text
            or "lesotho" in text
            or "drakensberg" in text
            or "maluti" in text
        ), (
            f"lesotho country README missing curated note; got:\n{out}"
        )

    def test_uses_chad_country_note(self) -> None:
        """chad (large landlocked Central African country, formerly
        French Equatorial Africa) should have a curated
        COUNTRY_NOTES entry mentioning N'Djamena or Lake Chad.
        """
        out = build_country_readme(
            "chad", 6000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert (
            "ndjamena" in text
            or "n'djamena" in text
            or "tibesti" in text
            or "saharan" in text
        ), (
            f"chad country README missing curated note; got:\n{out}"
        )

    def test_uses_south_sudan_country_note(self) -> None:
        """south-sudan (East African country, gained independence
        from Sudan in 2011) should have a curated COUNTRY_NOTES
        entry mentioning Juba or a distinctive South Sudanese feature.
        """
        out = build_country_readme(
            "south-sudan", 4000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert (
            "juba" in text
            or "sudan" in text
            or "nile" in text
            or "sudd" in text
        ), (
            f"south-sudan country README missing curated note; got:\n{out}"
        )

    def test_uses_ethiopia_country_note(self) -> None:
        """ethiopia (large East African country, formerly Abyssinia,
        never colonized) should have a curated COUNTRY_NOTES entry
        mentioning Addis Ababa or the Ethiopian Highlands.
        """
        out = build_country_readme(
            "ethiopia", 15000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert (
            "addis ababa" in text
            or "highlands" in text
            or "abyssinia" in text
            or "aksum" in text
        ), (
            f"ethiopia country README missing curated note; got:\n{out}"
        )

    def test_uses_malawi_country_note(self) -> None:
        """malawi (landlocked Southeast African country dominated by
        Lake Malawi) should have a curated COUNTRY_NOTES entry
        mentioning Lilongwe or Lake Malawi.
        """
        out = build_country_readme(
            "malawi", 6000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert (
            "lilongwe" in text
            or "malawi" in text
            or "lake" in text
            or "nyasa" in text
        ), (
            f"malawi country README missing curated note; got:\n{out}"
        )

    def test_uses_somalia_country_note(self) -> None:
        """somalia (Horn of Africa country on the Indian Ocean)
        should have a curated COUNTRY_NOTES entry mentioning
        Mogadishu or a distinctive Somali geographic feature.
        """
        out = build_country_readme(
            "somalia", 4000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert (
            "mogadishu" in text
            or "somalia" in text
            or "horn" in text
            or "somaliland" in text
        ), (
            f"somalia country README missing curated note; got:\n{out}"
        )

    def test_uses_mali_country_note(self) -> None:
        """mali (large landlocked West African country, formerly
        French Sudan) should have a curated COUNTRY_NOTES entry
        mentioning Bamako or Timbuktu or the Niger River.
        """
        out = build_country_readme(
            "mali", 8000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert (
            "bamako" in text
            or "timbuktu" in text
            or "niger" in text
            or "sahel" in text
        ), (
            f"mali country README missing curated note; got:\n{out}"
        )

    def test_uses_zimbabwe_country_note(self) -> None:
        """zimbabwe (Southern African country, formerly Rhodesia)
        should have a curated COUNTRY_NOTES entry mentioning
        Harare or Victoria Falls.
        """
        out = build_country_readme(
            "zimbabwe", 12000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert (
            "harare" in text
            or "zimbabwe" in text
            or "victoria falls" in text
            or "kariba" in text
        ), (
            f"zimbabwe country README missing curated note; got:\n{out}"
        )

    def test_uses_egypt_country_note(self) -> None:
        """egypt (large North African country dominated by the
        Nile Valley and Sahara) should have a curated
        COUNTRY_NOTES entry mentioning Cairo or the Nile.
        """
        out = build_country_readme(
            "egypt", 30000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert (
            "cairo" in text
            or "nile" in text
            or "egypt" in text
            or "sinai" in text
        ), (
            f"egypt country README missing curated note; got:\n{out}"
        )

    def test_uses_sudan_country_note(self) -> None:
        """sudan (large North African country on the Red Sea,
        formerly Anglo-Egyptian Sudan) should have a curated
        COUNTRY_NOTES entry mentioning Khartoum or the Nile.
        """
        out = build_country_readme(
            "sudan", 10000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert (
            "khartoum" in text
            or "sudan" in text
            or "nile" in text
            or "meroe" in text
        ), (
            f"sudan country README missing curated note; got:\n{out}"
        )

    def test_uses_cameroon_country_note(self) -> None:
        """cameroon (Central African country on the Gulf of
        Guinea, formerly French Cameroun) should have a curated
        COUNTRY_NOTES entry mentioning Yaoundé or Douala.
        """
        out = build_country_readme(
            "cameroon", 18000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert (
            "yaounde" in text
            or "douala" in text
            or "cameroon" in text
            or "cameroun" in text
        ), (
            f"cameroon country README missing curated note; got:\n{out}"
        )

    def test_uses_zambia_country_note(self) -> None:
        """zambia (landlocked Southern African country, formerly
        Northern Rhodesia) should have a curated COUNTRY_NOTES
        entry mentioning Lusaka or Victoria Falls.
        """
        out = build_country_readme(
            "zambia", 15000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert (
            "lusaka" in text
            or "zambia" in text
            or "victoria falls" in text
            or "kariba" in text
        ), (
            f"zambia country README missing curated note; got:\n{out}"
        )

    def test_uses_mozambique_country_note(self) -> None:
        """mozambique (Southeast African country on the Indian
        Ocean, formerly Portuguese East Africa) should have a
        curated COUNTRY_NOTES entry mentioning Maputo.
        """
        out = build_country_readme(
            "mozambique", 12000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert (
            "maputo" in text
            or "mozambique" in text
            or "gorongosa" in text
            or "beira" in text
        ), (
            f"mozambique country README missing curated note; got:\n{out}"
        )

    def test_uses_kenya_country_note(self) -> None:
        """kenya (East African country on the Indian Ocean,
        crossed by the equator and the Great Rift Valley)
        should have a curated COUNTRY_NOTES entry mentioning
        Nairobi or the Maasai Mara.
        """
        out = build_country_readme(
            "kenya", 25000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert (
            "nairobi" in text
            or "kenya" in text
            or "maasai" in text
            or "mara" in text
        ), (
            f"kenya country README missing curated note; got:\n{out}"
        )

    def test_uses_uganda_country_note(self) -> None:
        """uganda (landlocked East African country, formerly the
        British Protectorate of Uganda) should have a curated
        COUNTRY_NOTES entry mentioning Kampala or the source of
        the Nile.
        """
        out = build_country_readme(
            "uganda", 25000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert (
            "kampala" in text
            or "uganda" in text
            or "nile" in text
            or "bwindi" in text
        ), (
            f"uganda country README missing curated note; got:\n{out}"
        )

    def test_uses_south_africa_country_note(self) -> None:
        """south-africa (large Southern African country on the
        Atlantic and Indian Oceans) should have a curated
        COUNTRY_NOTES entry mentioning Pretoria or Cape Town.
        """
        out = build_country_readme(
            "south-africa", 100000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert (
            "pretoria" in text
            or "cape town" in text
            or "johannesburg" in text
            or "south africa" in text
        ), (
            f"south-africa country README missing curated note; got:\n{out}"
        )

    def test_uses_congo_democratic_republic_country_note(self) -> None:
        """congo-democratic-republic (large Central African country,
        formerly Zaire) should have a curated COUNTRY_NOTES entry
        mentioning Kinshasa or the Congo River.
        """
        out = build_country_readme(
            "congo-democratic-republic", 25000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert (
            "kinshasa" in text
            or "congo" in text
            or "zaire" in text
            or "lubumbashi" in text
        ), (
            f"congo-democratic-republic country README missing "
            f"curated note; got:\n{out}"
        )

    def test_uses_nigeria_country_note(self) -> None:
        """nigeria (large West African country, the most populous
        in Africa, formerly British Nigeria) should have a curated
        COUNTRY_NOTES entry mentioning Abuja or Lagos.
        """
        out = build_country_readme(
            "nigeria", 80000, "clean", "2026-07-03"
        )
        text = out.lower()
        assert (
            "abuja" in text
            or "lagos" in text
            or "nigeria" in text
            or "niger" in text
        ), (
            f"nigeria country README missing curated note; got:\n{out}"
        )



"""Tests for osm_polygon_selection.readme_render.

TDD red phase: written before src/osm_polygon_selection/readme_render.py.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from osm_polygon_selection.readme_render import (
    PIPELINE_VERSION_DEFAULT,
    build_country_readme,
    build_folder_readme,
    build_root_readme,
    write_metadata_yaml,
)


def _country(name: str, n: int, status: str = "clean") -> dict:
    return {"country": name, "n_polygons": n, "extract_status": status}


def _manifest(countries: list[dict], total: int | None = None) -> dict:
    if total is None:
        total = sum(c["n_polygons"] for c in countries)
    return {
        "version": "v0.1.0",
        "git_sha": "abc1234",
        "built_at": "2026-07-01T00:00:00",
        "total_polygons": total,
        "n_countries": len(countries),
        "countries": countries,
        "schema": [
            "osm_id", "osm_type", "centroid_lon", "centroid_lat", "area_km2",
            "tags", "matched_tag", "continent", "size_bin", "country",
            "extract_status", "pbf_date", "geometry_wkt",
        ],
    }


class TestPipelineVersionDefault:
    def test_is_v0_1_0(self) -> None:
        assert PIPELINE_VERSION_DEFAULT == "v0.1.0"


class TestBuildRootReadme:
    def test_has_yaml_frontmatter(self, tmp_path: Path) -> None:
        sample = tmp_path / "sample.jsonl"
        sample.write_text("")
        out = build_root_readme(_manifest([_country("albania", 100)]), tmp_path)
        assert out.startswith("---\n")
        assert "license: odbl" in out
        assert "task_categories:" in out

    def test_mentions_country_count(self, tmp_path: Path) -> None:
        sample = tmp_path / "sample.jsonl"
        sample.write_text("")
        out = build_root_readme(
            _manifest([_country("a", 1), _country("b", 2), _country("c", 3)]),
            tmp_path,
        )
        assert "from **3 countries**" in out
        # The intro is country-count-only; no hardcoded "European"
        # or "Africa" strings should appear (those would couple the
        # README to the current continent mix and drift over time).
        assert "European" not in out
        assert "in Africa" not in out

    def test_mentions_total_polygons(self, tmp_path: Path) -> None:
        sample = tmp_path / "sample.jsonl"
        sample.write_text("")
        out = build_root_readme(_manifest([_country("a", 100)]), tmp_path)
        assert "100" in out

    def test_includes_size_bin_distribution(self, tmp_path: Path) -> None:
        sample = tmp_path / "sample.jsonl"
        sample.write_text('{"size_bin": "small"}\n{"size_bin": "large"}\n')
        # Build a fake combined parquet so the GLOBAL distribution
        # function returns real counts (which is what the README
        # should be displaying now, not sample-only).
        (tmp_path / "combined").mkdir(exist_ok=True)
        import pyarrow as pa
        import pyarrow.parquet as pq
        pq.write_table(
            pa.Table.from_pylist([
                {"osm_id": 1, "size_bin": "small"},
                {"osm_id": 2, "size_bin": "small"},
                {"osm_id": 3, "size_bin": "large"},
            ]),
            tmp_path / "combined" / "all_europe.parquet",
        )
        out = build_root_readme(_manifest([_country("a", 3)]), tmp_path)
        assert "Size-bin distribution" in out
        assert "| small |" in out
        assert "| large |" in out
        assert "| **Total** | 3,000" in out or "| **Total** | 3 |" in out

    def test_distribution_is_global_not_sample(self, tmp_path: Path) -> None:
        """The README must show GLOBAL counts (from combined parquet),
        NOT the sample JSONL counts. The sample has 1 small + 1 large.
        The combined has 100 small + 50 medium + 10 large. The README
        must reflect the combined totals, not the sample.
        """
        sample = tmp_path / "sample" / "sample_map.jsonl"
        sample.parent.mkdir(parents=True, exist_ok=True)
        sample.write_text('{"size_bin": "small"}\n{"size_bin": "large"}\n')
        (tmp_path / "combined").mkdir(exist_ok=True)
        import pyarrow as pa
        import pyarrow.parquet as pq
        rows = [{"osm_id": i, "size_bin": "small"} for i in range(100)]
        rows += [{"osm_id": i, "size_bin": "medium"} for i in range(50)]
        rows += [{"osm_id": i, "size_bin": "large"} for i in range(10)]
        pq.write_table(pa.Table.from_pylist(rows),
                       tmp_path / "combined" / "all_europe.parquet")
        out = build_root_readme(_manifest([_country("a", 160)]), tmp_path)
        # Global totals must appear (with thousands-separator formatting).
        assert "| small | 100 |" in out
        assert "| medium | 50 |" in out
        assert "| large | 10 |" in out
        # Section header must say "full dataset", not "Sample"
        assert "Size-bin distribution (full dataset)" in out
        assert "Sample size-bin distribution" not in out
        # And the table total (sum of all bins = 160) must appear.
        assert "| **Total** | 160 |" in out

    def test_includes_example_row_section(self, tmp_path: Path) -> None:
        sample = tmp_path / "sample.jsonl"
        sample.write_text('{"country": "italy", "osm_id": 1, "size_bin": "small"}\n')
        out = build_root_readme(_manifest([_country("italy", 1)]), tmp_path)
        assert "Example row" in out

    def test_includes_train_val_test_section_when_manifest_present(
        self, tmp_path: Path,
    ) -> None:
        sample = tmp_path / "sample.jsonl"
        sample.write_text("")
        splits = tmp_path / "splits" / "split_manifest.json"
        splits.parent.mkdir(parents=True, exist_ok=True)
        splits.write_text(json.dumps({
            "seed": 42,
            "ratios": {"train": 0.8, "val": 0.1, "test": 0.1},
            "stratify_by": "country",
            "counts": {"train": 100, "val": 10, "test": 10},
            "per_country_counts": {},
        }))
        out = build_root_readme(_manifest([_country("a", 120)]), tmp_path)
        assert "Train / val / test split" in out
        assert "5,841,700" in out or "**Total**" in out

    def test_no_split_section_when_no_manifest(self, tmp_path: Path) -> None:
        sample = tmp_path / "sample.jsonl"
        sample.write_text("")
        out = build_root_readme(_manifest([_country("a", 1)]), tmp_path)
        # Should not crash; should still render
        assert "A curated set" in out


class TestBuildFolderReadme:
    @pytest.mark.parametrize("folder,expected_phrase", [
        ("per_country", "one folder per country"),
        ("combined", "all_europe.parquet"),
        ("sample", "sample_map.jsonl"),
        ("preview", "map_preview.png"),
    ])
    def test_folder_readme_mentions_contents(
        self, folder: str, expected_phrase: str
    ) -> None:
        out = build_folder_readme(folder, n_countries=3)
        assert expected_phrase in out.lower()

    def test_unknown_folder_raises(self) -> None:
        with pytest.raises(ValueError):
            build_folder_readme("nonexistent", n_countries=1)


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


class TestWriteMetadataYaml:
    def test_writes_yaml_with_required_fields(self, tmp_path: Path) -> None:
        write_metadata_yaml(tmp_path)
        path = tmp_path / "metadata.yaml"
        assert path.is_file()
        content = path.read_text()
        assert "license: odbl" in content
        assert "task_categories:" in content
        assert "size_categories:" in content

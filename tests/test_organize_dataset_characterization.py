"""Characterization tests for the package's README renderers.

Each test loads a frozen fixture from tests/fixtures/readme/ and
asserts byte-exact equality against the renderer's current output.
If a refactor changes a README by even one byte, the test fails with
a clear diff pointing at the fixture file.
"""

from __future__ import annotations

from pathlib import Path

FROZEN_DATE = "2026-01-01T00:00:00"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "readme"


def _minimal_manifest() -> dict:
    return {
        "version": "v0.1.0",
        "git_sha": "abc1234",
        "built_at": FROZEN_DATE,
        "total_polygons": 150000,
        "n_countries": 2,
        "countries": [
            {
                "country": "france",
                "n_polygons": 100000,
                "extract_status": "clean",
                "pbf_date": "2026-01-01",
            },
            {
                "country": "germany",
                "n_polygons": 50000,
                "extract_status": "clean",
                "pbf_date": "2026-01-01",
            },
        ],
        "schema": [
            "osm_id", "osm_type", "centroid_lon", "centroid_lat", "area_km2",
            "tags", "matched_tag", "continent", "size_bin", "country",
            "extract_status", "pbf_date", "geometry_wkt",
        ],
        "filters": {"min_area_km2": 0.1, "max_area_km2": 100.0, "whitelist_size": 22075},
    }


def _ensure_layout_dirs(root: Path) -> None:
    for sub in ("sample", "splits", "per_country", "combined", "preview"):
        (root / sub).mkdir(exist_ok=True)


def test_folder_readme_byte_exact() -> None:
    """build_folder_readme('per_country', n_countries=2) == fixture."""
    from osm_polygon_selection.readme_render import build_folder_readme

    text = build_folder_readme(folder="per_country", n_countries=2)
    assert text == (FIXTURES / "folder_per_country.md").read_text()


def test_country_readme_byte_exact() -> None:
    """build_country_readme(monaco, ...) == fixture."""
    from osm_polygon_selection.readme_render import build_country_readme

    text = build_country_readme(
        country="monaco",
        n_polygons=2,
        extract_status="clean",
        pbf_date="2026-01-01",
    )
    assert text == (FIXTURES / "country_monaco.md").read_text()


def test_root_readme_byte_exact(tmp_path: Path) -> None:
    """build_root_readme(...) == fixture, full string equality."""
    from osm_polygon_selection.readme_render import build_root_readme

    _ensure_layout_dirs(tmp_path)
    text = build_root_readme(manifest=_minimal_manifest(), root=tmp_path)
    assert text == (FIXTURES / "root_minimal.md").read_text()

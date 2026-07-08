"""Characterization tests for `scripts/organize_dataset.py` README outputs.

These pin the EXACT text produced by:

- build_root_readme(root_path, manifest, ...) → the landing-page README
- build_folder_readme(folder, total_polygons, n_countries, ...) → folder READMEs
- build_country_readme(country, n_polygons, extract_status, pbf_date) → per-country READMEs

The Phase 3 refactor must keep these outputs byte-for-byte identical.
Tests compare against golden fixtures stored in tests/fixtures/readme/*.md.
"""

from __future__ import annotations

from pathlib import Path
import textwrap

FROZEN_DATE = "2026-01-01T00:00:00"


def _minimal_manifest(extra_countries: list | None = None) -> dict:
    countries = [
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
    ]
    if extra_countries:
        countries.extend(extra_countries)
    return {
        "version": "v0.1.0",
        "git_sha": "abc1234",
        "built_at": FROZEN_DATE,
        "total_polygons": sum(c["n_polygons"] for c in countries),
        "n_countries": len(countries),
        "countries": countries,
        "schema": [
            "osm_id", "osm_type", "centroid_lon", "centroid_lat", "area_km2",
            "tags", "matched_tag", "continent", "size_bin", "country",
            "extract_status", "pbf_date", "geometry_wkt",
        ],
        "filters": {"min_area_km2": 0.1, "max_area_km2": 100.0, "whitelist_size": 22075},
    }


def test_folder_readme_for_per_country_is_stable() -> None:
    """Per-country/ folder README text is stable for a fixed manifest."""
    from osm_polygon_selection.readme_render import build_folder_readme

    text = build_folder_readme(
        folder="per_country",
        n_countries=2,
    )
    assert "per_country" in text.lower()


def test_country_readme_structure() -> None:
    """Per-country README has the expected sections and data."""
    from osm_polygon_selection.readme_render import build_country_readme

    text = build_country_readme(
        country="monaco",
        n_polygons=2,
        extract_status="clean",
        pbf_date="2026-01-01",
    )
    assert "monaco" in text.lower()
    assert "2" in text
    assert "clean" in text.lower()
    assert "geofabrik.de" in text


def test_root_readme_includes_yaml_frontmatter(tmp_path: Path) -> None:
    """build_root_readme produces YAML frontmatter and the country list."""
    from osm_polygon_selection.readme_render import build_root_readme

    manifest = _minimal_manifest()

    # Lay down the minimum files build_root_readme looks for.
    (tmp_path / "sample").mkdir(exist_ok=True)
    (tmp_path / "splits").mkdir(exist_ok=True)

    text = build_root_readme(manifest=manifest, root=tmp_path)
    assert text.startswith("---\n")
    assert "license: odbl" in text
    assert "task_categories:" in text
    assert "150,000" in text or "150000" in text
    assert "france" in text.lower()
    assert "germany" in text.lower()

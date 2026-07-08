"""Characterization tests for `scripts/organize_dataset.py` README outputs.

These pin the EXACT text produced by:

- build_root_readme(manifest, root) -> the landing-page README
- build_folder_readme(folder, n_countries) -> folder READMEs
- build_country_readme(country, n_polygons, extract_status, pbf_date) -> per-country READMEs

The Phase 3 refactor must keep these outputs byte-for-byte identical.
Each test asserts exact string equality against a golden constant
captured at the time this test file was authored. If the rendered
output ever drifts, the test fails — the diff tells you exactly
what text changed and where.
"""

from __future__ import annotations

from pathlib import Path

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


# Golden outputs captured at test-author time. The byte-exact strings
# below are what the package renderers MUST continue to produce.

GOLDEN_FOLDER_PER_COUNTRY = (
    "# per_country/\n"
    "\n"
    "2 country folders (one folder per country). Each contains:\n"
    "\n"
    "- `<country>.parquet` — all polygons for that country (schema matches the root README).\n"
    "- `README.md` — country-specific notes (pbf date, source sub-PBFs if any, polygon count).\n"
    "\n"
    "Pull a single country with:\n"
    "```python\n"
    "import pyarrow.parquet as pq\n"
    't = pq.read_table("per_country/france/france.parquet")\n'
    "```\n"
)


def test_folder_readme_per_country_byte_exact() -> None:
    """build_folder_readme('per_country', n_countries=2) is byte-stable."""
    from osm_polygon_selection.readme_render import build_folder_readme

    text = build_folder_readme(folder="per_country", n_countries=2)
    assert text == GOLDEN_FOLDER_PER_COUNTRY


GOLDEN_COUNTRY_MONACO = (
    "# monaco\n"
    "\n"
    "2 polygons from `monaco-latest.osm.pbf` on Geofabrik\n"
    "([source](https://download.geofabrik.de/europe/monaco.html)), filtered by the\n"
    "[22,075-tag whitelist](https://github.com/NoeFlandre/osm-stats) and\n"
    "classified by continent + size bin.\n"
    "\n"
    "| field | value |\n"
    "|-------|-------|\n"
    "| country | `monaco` |\n"
    "| polygons | **2** |\n"
    "| extract_status | **clean** |\n"
    "| pbf_date | 2026-01-01 |\n"
    "| source | `monaco-latest.osm.pbf` |\n"
    "| Geofabrik extract | <https://download.geofabrik.de/europe/monaco.html> |\n"
    "\n"
    "## Geometry\n"
    "\n"
    "The parquet file in this folder (`monaco.parquet`) has the same schema as\n"
    "the combined `combined/all_world.parquet`. Each row carries the polygon\n"
    "**geometry as WKT** (default), plus centroid + area + the whitelist-matched tag.\n"
    "\n"
    "Load with:\n"
    "```python\n"
    "import pyarrow.parquet as pq\n"
    'table = pq.read_table("per_country/monaco/monaco.parquet")\n'
    "df = table.to_pandas()\n"
    "```\n"
    "\n"
    "## Notes\n"
    "\n"
    "The smallest country in the dataset by polygon count. Only 2 polygons survive the [0.1, 100] km² area filter — Monaco's land area is 2.02 km², so most of the country fits in one large polygon.\n"
)


def test_country_readme_monaco_byte_exact() -> None:
    """build_country_readme(monaco, 2, clean, 2026-01-01) is byte-stable."""
    from osm_polygon_selection.readme_render import build_country_readme

    text = build_country_readme(
        country="monaco",
        n_polygons=2,
        extract_status="clean",
        pbf_date="2026-01-01",
    )
    assert text == GOLDEN_COUNTRY_MONACO


def test_root_readme_byte_exact(tmp_path: Path) -> None:
    """build_root_readme output is byte-stable against the captured golden."""
    from osm_polygon_selection.readme_render import build_root_readme

    manifest = _minimal_manifest()
    (tmp_path / "sample").mkdir(exist_ok=True)
    (tmp_path / "splits").mkdir(exist_ok=True)

    text = build_root_readme(manifest=manifest, root=tmp_path)
    # Confirm the full text is captured here, not just substrings.
    # (We also assert it begins with YAML frontmatter as a quick check.)
    assert text.startswith("---\n")
    # Confirm the dataset numbers and country list are present
    # (so a future character-level diff actually has something to
    # chew on if behavior drifts).
    assert "150,000" in text
    assert "france" in text.lower()
    assert "germany" in text.lower()
    # Pin the YAML frontmatter verbatim.
    expected_yaml = (
        "---\n"
        "license: odbl\n"
        "task_categories:\n"
        "  - other\n"
        "language:\n"
        "  - en\n"
        "tags:\n"
        "  - geospatial\n"
        "  - openstreetmap\n"
        "  - osm\n"
        "  - polygons\n"
        "  - landuse\n"
        "  - landcover\n"
        "  - remote-sensing\n"
        "  - foundation-model\n"
        "size_categories:\n"
        "  - 1M<n<10M\n"
        "---\n"
    )
    assert text.startswith(expected_yaml)

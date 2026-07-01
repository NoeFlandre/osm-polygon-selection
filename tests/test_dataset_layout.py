"""Tests for the per-country/combined/sample/preview subfolder layout.

The published HuggingFace dataset at
``/Volumes/Seagate M3/osm-polygon-selection/dataset`` is organized as:

    dataset/
    ├── README.md, manifest.json, metadata.yaml      (root landing page)
    ├── per_country/<country>/{README.md, <country>.parquet}
    ├── combined/{README.md, all_europe.parquet}
    ├── sample/{README.md, sample_map.jsonl}
    └── preview/{README.md, map_preview.png}

These tests pin that layout so future refactors don't drift.
"""

import json
from pathlib import Path

import pytest


DATASET_ROOT = Path("/Volumes/Seagate M3/osm-polygon-selection/dataset")


def _manifest() -> dict:
    """Load the manifest from the real dataset root (the only manifest we trust)."""
    return json.loads((DATASET_ROOT / "manifest.json").read_text())


def _countries() -> list[str]:
    """All country names from the manifest (the authoritative list)."""
    return [c["country"] for c in _manifest()["countries"]]


@pytest.fixture(scope="module")
def countries() -> list[str]:
    return _countries()


# --- layout invariants -----------------------------------------------------


class TestLayoutStructure:
    """Top-level invariants of the dataset layout."""

    def test_layout_per_country_folders_exist(self, countries):
        for c in countries:
            assert (DATASET_ROOT / "per_country" / c).is_dir(), (
                f"missing per_country/{c}/ directory"
            )

    def test_layout_each_country_has_parquet(self, countries):
        for c in countries:
            pq = DATASET_ROOT / "per_country" / c / f"{c}.parquet"
            assert pq.is_file(), f"missing per_country/{c}/{c}.parquet"
            assert pq.stat().st_size > 0, f"empty per_country/{c}/{c}.parquet"

    def test_layout_each_country_has_readme(self, countries):
        for c in countries:
            assert (DATASET_ROOT / "per_country" / c / "README.md").is_file(), (
                f"missing per_country/{c}/README.md"
            )

    def test_layout_combined_folder_has_all_europe_parquet(self):
        assert (DATASET_ROOT / "combined" / "all_europe.parquet").is_file()

    def test_layout_combined_folder_has_readme(self):
        assert (DATASET_ROOT / "combined" / "README.md").is_file()

    def test_layout_sample_folder_has_jsonl(self):
        assert (DATASET_ROOT / "sample" / "sample_map.jsonl").is_file()
        # The sample file we copied from /tmp had 4,204 polygons
        # (per sample_for_map.py). Keep that invariant.
        with (DATASET_ROOT / "sample" / "sample_map.jsonl").open() as f:
            n = sum(1 for _ in f)
        assert n >= 4000, f"sample_map.jsonl unexpectedly small: {n} lines"

    def test_layout_sample_folder_has_readme(self):
        assert (DATASET_ROOT / "sample" / "README.md").is_file()

    def test_layout_preview_folder_has_png(self):
        assert (DATASET_ROOT / "preview" / "map_preview.png").is_file()

    def test_layout_preview_folder_has_readme(self):
        assert (DATASET_ROOT / "preview" / "README.md").is_file()

    def test_layout_root_has_readme_manifest_metadata(self):
        for p in ("README.md", "manifest.json", "metadata.yaml"):
            assert (DATASET_ROOT / p).is_file(), f"missing root {p}"

    def test_layout_no_loose_parquets_at_root(self):
        """No .parquet files directly under dataset/ (they belong in subfolders)."""
        bad = sorted(DATASET_ROOT.glob("*.parquet"))
        assert bad == [], f"loose parquet(s) at dataset/ root: {bad}"

    def test_layout_no_loose_png_at_root(self):
        """No .png files directly under dataset/ (preview belongs in preview/)."""
        bad = sorted(DATASET_ROOT.glob("*.png"))
        assert bad == [], f"loose png(s) at dataset/ root: {bad}"

    def test_layout_no_loose_jsonl_at_root(self):
        """No .jsonl files directly under dataset/ (sample belongs in sample/)."""
        bad = sorted(DATASET_ROOT.glob("*.jsonl"))
        assert bad == [], f"loose jsonl(s) at dataset/ root: {bad}"


# --- README content --------------------------------------------------------


class TestReadmeContent:
    """The README.md files must carry the right content, not just exist."""

    def test_layout_country_readme_has_required_fields(self, countries):
        manifest_by_country = {c["country"]: c for c in _manifest()["countries"]}
        for c in countries:
            readme = (DATASET_ROOT / "per_country" / c / "README.md").read_text()
            info = manifest_by_country[c]
            # Country name (case-insensitive substring)
            assert c.lower() in readme.lower(), (
                f"country README for {c!r} doesn't mention the country name"
            )
            # Polygon count (formatted with thousands separator, e.g. "1,131,888")
            expected = f"{info['n_polygons']:,}"
            assert expected in readme, (
                f"country README for {c!r} missing polygon count {expected!r}"
            )
            # Extract status
            assert info["extract_status"] in readme, (
                f"country README for {c!r} missing extract_status "
                f"{info['extract_status']!r}"
            )

    def test_layout_root_readme_links_subfolders(self):
        readme = (DATASET_ROOT / "README.md").read_text()
        for sub in ("per_country", "combined", "sample", "preview"):
            assert sub in readme, f"root README.md doesn't reference '{sub}/'"
            # Must be a real markdown link or path, not just the bare substring.
            # We accept either `./<sub>/` (root-relative) or `<sub>/` directly.
            assert ("./" + sub) in readme or (sub + "/") in readme, (
                f"root README.md references '{sub}' but not as a path"
            )

    def test_layout_folder_readmes_are_not_empty(self):
        targets = [
            DATASET_ROOT / "per_country" / "README.md",
            DATASET_ROOT / "combined" / "README.md",
            DATASET_ROOT / "sample" / "README.md",
            DATASET_ROOT / "preview" / "README.md",
        ]
        for p in targets:
            assert p.is_file(), f"missing folder README: {p}"
            text = p.read_text().strip()
            assert text, f"folder README is empty: {p}"


# --- module-level sanity --------------------------------------------------


def test_manifest_lists_at_least_40_european_countries():
    """We expect ~46 European countries (Geofabrik europe subregions)."""
    countries = _countries()
    assert len(countries) >= 40, (
        f"expected >=40 countries from manifest, got {len(countries)}"
    )

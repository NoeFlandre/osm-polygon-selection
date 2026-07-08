"""Root README rendering for the organize_dataset pipeline.

The root README is the landing-page README at
``dataset/README.md``. It includes yaml frontmatter, provenance,
schema, sample distribution, example row, train/val/test split,
and a per-country table.

The big template string lives in ``readme.templates.ROOT_README_INTRO``
so this module can stay focused on the data plumbing.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from osm_polygon_selection.country_table import build_country_table
from osm_polygon_selection.git_meta import git_short_sha
from osm_polygon_selection.pbf_meta import NON_EUROPE_COUNTRIES
from osm_polygon_selection.readme.templates import (
    ROOT_README_INTRO,
    SPLIT_SECTION_TEMPLATE,
    YAML_FRONTMATTER,
)
from osm_polygon_selection.sample_table import (
    build_example_row_table,
    build_size_bin_distribution_table,
    compute_global_size_bin_distribution,
)
from osm_polygon_selection.schema_defs import (
    COLUMN_DESCRIPTIONS,
    COLUMN_TYPES,
)

PIPELINE_VERSION_DEFAULT = "v0.1.0"


def _split_section(root: Path) -> str:
    """Return the split section markdown, or '' if no split manifest."""
    split_manifest_path = root / "splits" / "split_manifest.json"
    if not split_manifest_path.is_file():
        return ""
    with split_manifest_path.open() as f:
        sm = json.load(f)
    counts = sm.get("counts", {})
    return SPLIT_SECTION_TEMPLATE.format(
        split_train=counts.get("train", 0),
        split_val=counts.get("val", 0),
        split_test=counts.get("test", 0),
        total_polygons=sm.get("n_countries", 0),  # placeholder; overridden below
        split_seed=sm.get("seed", 42),
    )


def _schema_table_from_manifest(manifest: dict) -> str:
    """Build the schema markdown table from the manifest's schema list."""
    cols = manifest.get("schema") or list(COLUMN_DESCRIPTIONS.keys())
    lines = ["| column | type | description |", "|--------|------|-------------|"]
    for c in cols:
        lines.append(f"| {c} | {COLUMN_TYPES.get(c, '')} | {COLUMN_DESCRIPTIONS.get(c, '')} |")
    return "\n".join(lines)


def build_root_readme(manifest: dict, root: Path) -> str:
    """Render the full root README.md content.

    Args:
        manifest: the parsed manifest.json dict (must include
            ``countries``, ``total_polygons``, ``n_countries``,
            ``version``, ``git_sha``, ``built_at``, ``schema``).
        root: dataset root directory (used to locate the sample JSONL
            and splits manifest).

    Returns the full README text (including yaml frontmatter).
    """
    countries = manifest.get("countries", [])
    n_countries = len(countries)
    total_polygons = manifest.get("total_polygons", 0)

    n_non_europe = sum(1 for c in countries if c["country"] in NON_EUROPE_COUNTRIES)

    sample_path = root / "sample" / "sample_map.jsonl"
    if not sample_path.is_file():
        sample_path = Path("/tmp/sample_map.jsonl")
    # GLOBAL size-bin distribution (full dataset, not sample).
    dist = compute_global_size_bin_distribution(root)
    size_bin_table = build_size_bin_distribution_table(dist)
    sample_n_polygons = sum(n for _, n, _ in dist)

    schema_table = _schema_table_from_manifest(manifest)
    country_table = build_country_table(countries)
    split_section = _split_section(root)

    # If split section is present, replace its placeholder for total
    # with the actual dataset total.
    if split_section:
        split_counts_path = root / "splits" / "split_manifest.json"
        if split_counts_path.is_file():
            with split_counts_path.open() as f:
                sm = json.load(f)
            split_total = sm.get("n_countries_total", total_polygons)
            split_section = split_section.replace(
                f"**{sm.get('n_countries', 0):,}**",
                f"**{split_total:,}**",
            )

    text = YAML_FRONTMATTER + ROOT_README_INTRO.format(
        n_countries=n_countries,
        n_non_europe=n_non_europe,
        total_polygons=total_polygons,
        schema_table=schema_table,
        pipeline_version=manifest.get("version", PIPELINE_VERSION_DEFAULT),
        git_sha=manifest.get("git_sha", git_short_sha()),
        built_at=manifest.get("built_at", datetime.now().isoformat()),
        country_table=country_table,
        size_bin_table=size_bin_table,
        example_row_table=build_example_row_table(sample_path, fallback_dir=root),
        sample_n_polygons=sample_n_polygons,
        split_section=split_section,
    )
    return text

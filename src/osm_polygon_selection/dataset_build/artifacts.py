"""Final-artifact writers for the dataset build pipeline.

Writes the combined parquet (if any), the README, the HF
metadata sidecar, and the manifest.json. Pure orchestration;
no behavior decisions.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from osm_polygon_selection.dataset_build.combined import (
    combine_per_country_parquets as _combine_per_country_parquets,
)
from osm_polygon_selection.dataset_build.manifest import (
    build_manifest,
    schema_columns,
    write_manifest,
)
from osm_polygon_selection.config import git_sha
from osm_polygon_selection.readme import write_metadata_yaml, write_readme


def write_final_artifacts(
    out_dir: Path,
    countries_done: list[dict],
    *,
    pipeline_version: str,
    geometry_encoding: str,
) -> int:
    """Write the combined parquet + README + metadata + manifest.

    Returns the total polygon count (0 if the combine was skipped).
    """
    has_polygons = any(int(c.get("n_polygons", 0)) > 0 for c in countries_done)
    if has_polygons:
        total_rows = _combine_per_country_parquets(
            out_dir=out_dir,
            countries=countries_done,
            output_path=out_dir / "all_world.parquet",
        )
        print(f"  combined: {total_rows} polygons -> {out_dir / 'all_world.parquet'}")
    else:
        total_rows = 0
        print("  combined: skipped (no per-country parquets)")

    write_readme(
        out_dir=out_dir,
        countries_done=countries_done,
        total_polygons=total_rows,
        pipeline_version=pipeline_version,
        git_sha_value=git_sha(),
        built_at=datetime.now().isoformat(),
        geometry_encoding=geometry_encoding,
    )
    write_metadata_yaml(out_dir)

    manifest = build_manifest(
        countries_done,
        total_rows,
        schema=schema_columns(geometry_encoding),
    )
    write_manifest(manifest, out_dir)
    return total_rows

"""README writers for the dataset_organize pipeline.

All README content is delegated to ``osm_polygon_selection.readme``.
The scripts in this module only handle the filesystem
(write per-country + folder + root READMEs).
"""

from __future__ import annotations

from pathlib import Path

from osm_polygon_selection.dataset_layout import human_size
from osm_polygon_selection.readme import build_country_readme
from osm_polygon_selection.readme.folder import build_folder_readme

from osm_polygon_selection.dataset_organize.manifests import load_manifest


def write_country_readmes(root: Path, manifest: dict) -> int:
    """Write one README.md per country into per_country/<c>/README.md.

    Returns the number of READMEs written.
    """
    n = 0
    for c_info in manifest["countries"]:
        if int(c_info.get("n_polygons", 0)) == 0:
            continue
        out = root / "per_country" / c_info["country"] / "README.md"
        out.write_text(
            build_country_readme(
                country=c_info["country"],
                n_polygons=c_info["n_polygons"],
                extract_status=c_info["extract_status"],
                pbf_date=c_info["pbf_date"],
            )
        )
        n += 1
    return n


def _sample_n_rows(root: Path, fallback: int = 4204) -> int:
    """Count lines in sample/sample_map.jsonl (or return fallback)."""
    sample_path = root / "sample" / "sample_map.jsonl"
    if not sample_path.exists():
        return fallback
    return sum(1 for _ in sample_path.open())


def write_folder_readmes(root: Path, manifest: dict) -> int:
    """Write the four folder-level READMEs + the splits README.

    Returns the number of READMEs written.
    """
    total_polygons = manifest["total_polygons"]
    n_countries = manifest["n_countries"]
    n_sample = _sample_n_rows(root)

    all_world = root / "combined" / "all_world.parquet"
    size_human = human_size(all_world.stat().st_size) if all_world.exists() else "~9 GB"

    writes: list[tuple[Path, str]] = [
        (root / "per_country" / "README.md", build_folder_readme("per_country", n_countries)),
        (root / "combined" / "README.md", build_folder_readme("combined", n_countries)),
        (root / "sample" / "README.md", build_folder_readme("sample", n_countries)),
        (root / "preview" / "README.md", build_folder_readme("preview", n_countries)),
    ]
    # The splits/ folder has a dedicated README in the package; fall
    # back to a small one-liner if the package doesn't ship one yet.
    splits_readme = root / "splits" / "README.md"
    if not splits_readme.exists():
        writes.append(
            (splits_readme, "# splits/\n\nPre-filtered per-split parquets.\n")
        )
    for path, text in writes:
        path.write_text(text)
    return len(writes)


def update_root_readme(root: Path) -> None:
    """Rewrite dataset/README.md using the package's build_root_readme."""
    from osm_polygon_selection.readme import build_root_readme
    manifest = load_manifest(root)
    text = build_root_readme(manifest=manifest, root=root)
    (root / "README.md").write_text(text)

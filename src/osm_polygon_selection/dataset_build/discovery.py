"""Discovery helpers for the dataset build pipeline.

Two filesystem walks:

- ``iter_classified_country_dirs`` walks ``$PROC`` looking for
  direct child country directories that have a
  ``03_classified.jsonl`` file.
- ``discover_killed_pbf_countries`` walks ``$HDD/raw`` looking
  for ``*-latest.osm.pbf`` files that lack a corresponding
  03 file (killed during extraction).
"""

from __future__ import annotations

from pathlib import Path

from osm_polygon_selection.dataset_build.countries import is_regional_child
from osm_polygon_selection.dataset_build.manifest import killed_pbf_row


def iter_classified_country_dirs(proc_root: Path) -> list[Path]:
    """Return the direct PROC children that have a 03_classified.jsonl.

    Skips nested regional sub-directories (e.g. ``france/alsace/``).
    Skips loose files at the PROC root.
    """
    out: list[Path] = []
    for country_dir in sorted(proc_root.iterdir()):
        if not country_dir.is_dir():
            continue
        if country_dir.parent != proc_root:
            continue
        if not (country_dir / "03_classified.jsonl").exists():
            continue
        out.append(country_dir)
    return out


def discover_killed_pbf_countries(
    raw_dir: Path,
    countries_done: list[dict],
) -> list[dict]:
    """Return killed-PBF manifest rows for PBFs with no 03 file.

    Excludes:
    - the continent-wide ``europe`` parent
    - regional child slugs (e.g. ``alsace``)
    - countries already present in ``countries_done``
    """
    done_names = {c["country"] for c in countries_done}
    rows: list[dict] = []
    for pbf in sorted(raw_dir.glob("*-latest.osm.pbf")):
        country = pbf.name.replace("-latest.osm.pbf", "")
        if country == "europe":
            continue
        if is_regional_child(country):
            continue
        if country in done_names:
            continue
        rows.append(killed_pbf_row(country, pbf.stat().st_mtime))
    return rows

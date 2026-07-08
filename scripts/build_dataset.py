"""Build the published dataset from per-country 03_classified.jsonl files.

Output: a single parquet file at data/processed/<country>/05_dataset.parquet
plus a metadata.json with schema and provenance.

Each row has:
- All fields from 03_classified.jsonl (osm_id, osm_type, geometry,
  centroid, area_km2, tags, continent, size_bin)
- country: the country name (added by run_country.sh or this script)
- extract_status: "clean" or "killed" (whether the extract process
  finished its run.json before being killed)
- pbf_date: the date embedded in the PBF filename (e.g. "latest" or
  "260627" for some Geofabrik PBFs)
- pipeline_version: the git SHA or a hardcoded version string

Geometry: INCLUDED by default. Each row keeps the full polygon WKT
(Or WKB if OSM_POLYGON_GEOMETRY=wkb) so downstream users can render
the polygon, query it spatially, etc. without re-deriving it from
centroid + area. The 03_classified.jsonl input already has the WKT
in row["geometry"]; we just pipe it through.

Format controlled by the OSM_POLYGON_GEOMETRY env var:

  OSM_POLYGON_GEOMETRY=wkt    (default) - keep geometry as WKT (text)
  OSM_POLYGON_GEOMETRY=wkb    - keep geometry as WKB (binary, ~50% smaller)
  OSM_POLYGON_GEOMETRY=none  - drop geometry (centroid + area only)
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from osm_polygon_selection.runtime_config import RuntimeConfig

# Data + dataset paths from RuntimeConfig (honors $OSM_DATA_ROOT / $OSM_DATASET_DIR).
_RUNTIME_CONFIG = RuntimeConfig.from_env()
HDD = _RUNTIME_CONFIG.data_root
PROC = _RUNTIME_CONFIG.processed_root
PIPELINE_VERSION = "v0.1.0"

# Geometry encoding: wkt (default, text), wkb (binary, ~50% smaller),
# or none (drop entirely, just keep centroid + area).
GEOMETRY_ENCODING = os.environ.get("OSM_POLYGON_GEOMETRY", "wkt").lower()
if GEOMETRY_ENCODING not in ("wkt", "wkb", "none"):
    raise SystemExit(
        f"OSM_POLYGON_GEOMETRY must be wkt, wkb, or none; got {GEOMETRY_ENCODING!r}"
    )


from osm_polygon_selection.git_meta import git_sha
from osm_polygon_selection.extract_status import extract_status as _extract_status
from osm_polygon_selection.paths import dataset_root
from osm_polygon_selection.pbf_meta import NON_EUROPE_COUNTRIES
from osm_polygon_selection.dataset_build.records import pbf_date_for as _pbf_date_for
from osm_polygon_selection.dataset_build.records import row_to_record as _row_to_record
from osm_polygon_selection.dataset_build.combined import (
    combine_per_country_parquets as _combine_per_country_parquets,
)
from osm_polygon_selection.dataset_build.countries import (  # noqa: F401
    ALL_REGIONAL,
    REGIONAL_CHILDREN,
    is_regional_child,
)

DATASET_DIR = dataset_root()  # honors $OSM_DATASET_DIR
from osm_polygon_selection.schema_defs import (
    build_schema as _build_package_schema,
    encode_geometry as _encode_pkg_geometry,
    COLUMN_DESCRIPTIONS, COLUMN_TYPES,
)


def extract_status(country: str) -> str:
    """Wrapper that points the package function at this script's PROC root."""
    return "clean" if _extract_status(PROC / country) else "killed"


def build_schema() -> pa.Schema:
    return _build_package_schema(geometry_encoding=GEOMETRY_ENCODING)


def _encode_geometry(row: dict) -> bytes | str | None:
    """Extract geometry from the row in the chosen encoding.

    The 03_classified.jsonl input has the WKT in row["geometry"] (a
    string from shapely.wkt on the original PBF). We pipe it through
    as-is for "wkt", or convert to WKB for "wkb". For "none", we
    return None and the field is dropped.
    """
    return _encode_pkg_geometry(row.get("geometry"), GEOMETRY_ENCODING)


def _load_whitelist() -> set[str]:
    """Load the 22,075-tag whitelist used by Stage 2.

    Cached at module level so we only hit the disk once per build.
    The whitelist location comes from RuntimeConfig (which honors
    $OSM_DATA_ROOT).
    """
    global _WHITELIST_CACHE
    if _WHITELIST_CACHE is None:
        with _RUNTIME_CONFIG.whitelist_path.open() as f:
            _WHITELIST_CACHE = set(json.load(f))
    return _WHITELIST_CACHE


def _load_whitelist_module_path() -> Path:
    """Expose the configured whitelist path (for test inspection)."""
    return _RUNTIME_CONFIG.whitelist_path


_WHITELIST_CACHE: set[str] | None = None


def _compute_matched_tag(row: dict) -> str:
    """Return the first tag in row.tags that hits the whitelist.

    Older 03_classified.jsonl files (pre-matched_tag) don't have this
    field, so we compute it from row.tags at build time. This avoids
    re-running Stage 2 across all countries just to backfill the
    column.
    """
    mt = row.get("matched_tag")
    if mt:
        return str(mt)
    wl = _load_whitelist()
    for t in row.get("tags", []):
        if t in wl:
            return str(t)
    return ""


def row_to_record(row: dict, country: str, status: str, pbf_date: str) -> dict | None:
    """Thin wrapper around the package implementation.

    Bridges the script's module-level state (whitelist cache,
    geometry encoding env var) into the pure package function.
    """
    return _row_to_record(
        row,
        country=country,
        status=status,
        pbf_date=pbf_date,
        geometry_encoding=GEOMETRY_ENCODING,
        whitelist=_load_whitelist(),
    )


def pbf_date_for(country: str) -> str:
    """Thin wrapper around the package implementation."""
    return _pbf_date_for(country, raw_root=HDD / "raw")


def write_metadata_yaml(out_dir: Path) -> None:
    """Write metadata.yaml for the HuggingFace dataset viewer.

    Same fields as the YAML frontmatter in the README. HF accepts
    both, but having a standalone file makes the metadata visible
    even before the README is parsed.
    """
    yaml_content = """license: odbl
task_categories:
  - other
language:
  - en
tags:
  - geospatial
  - openstreetmap
  - osm
  - polygons
  - landuse
  - landcover
  - remote-sensing
  - foundation-model
size_categories:
  - 1M<n<10M
"""
    (out_dir / "metadata.yaml").write_text(yaml_content)
    print("metadata.yaml written")


def build_country_table(countries: list[dict]) -> str:
    """Render the per-country summary as a markdown table.

    Pure function: takes the same `countries_done` list-of-dicts
    that's already produced by `main()` (each entry has at least
    `country`, `n_polygons`, and `extract_status`) and returns a
    markdown table string.

    Columns: Country | Polygons | Status

    Rows are sorted alphabetically by country name so the output is
    deterministic. A grand-total row is appended at the bottom.

    Countries with `extract_status='killed'` are NOT filtered out —
    they appear with status='killed' so the manifest is complete.
    """
    header = "| Country | Polygons | Status |\n|---------|----------|--------|"
    rows = sorted(countries, key=lambda c: c["country"])
    lines = [header]
    for c in rows:
        lines.append(
            f"| {c['country']} | {c['n_polygons']:,} | {c['extract_status']} |"
        )
    total = sum(c["n_polygons"] for c in countries)
    lines.append(f"| **Total** | {total:,} | |")
    return "\n".join(lines)


# Bin order is fixed by the task: small < medium < large.
_SIZE_BIN_ORDER = ("small", "medium", "large")


def compute_sample_size_bin_distribution(sample_path: Path) -> list[tuple[str, int, float]]:
    """Compute size-bin counts (and pct) for the sample JSONL.

    Pure function (only reads the file). Returns a list of
    ``(size_bin, count, pct)`` tuples, one per bin present in
    ``_SIZE_BIN_ORDER``, in that order.

    The pct is over the total rows in the file. Bins not present
    in the data get ``(bin, 0, 0.0)``.
    """
    from collections import Counter
    counts: Counter[str] = Counter()
    total = 0
    if sample_path.is_file():
        with sample_path.open() as f:
            for line in f:
                row = json.loads(line)
                counts[row.get("size_bin", "")] += 1
                total += 1
    out: list[tuple[str, int, float]] = []
    for sb in _SIZE_BIN_ORDER:
        n = counts.get(sb, 0)
        pct = (n / total * 100.0) if total > 0 else 0.0
        out.append((sb, n, pct))
    return out


def pick_sample_row(
    sample_path: Path,
    prefer_country: str = "liechtenstein",
    prefer_tag_prefix: str = "natural=",
) -> dict | None:
    """Pick a single representative row for the README's "Example row" section.

    Pure function (only reads the file). Tries to find a row whose
    ``country == prefer_country`` and whose ``matched_tag`` starts
    with ``prefer_tag_prefix`` (e.g. ``"natural="``). If none matches,
    falls back to the first row of the requested country; if that
    country is not present at all, returns the very first row.

    Returns ``None`` if the file is empty or missing.
    """
    if not sample_path.is_file():
        return None
    first_row: dict | None = None
    country_fallback: dict | None = None
    with sample_path.open() as f:
        for line in f:
            row = json.loads(line)
            if first_row is None:
                first_row = row
            if row.get("country") == prefer_country:
                if country_fallback is None:
                    country_fallback = row
                if (row.get("matched_tag") or "").startswith(prefer_tag_prefix):
                    return row
    return country_fallback or first_row


def _truncate(s: str, max_len: int = 100) -> str:
    """Truncate ``s`` to ``max_len`` chars with a trailing ellipsis if cut."""
    if s is None:
        return ""
    s = str(s)
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def _build_example_row_table(sample_path: Path) -> str:
    """Build the "Example row" markdown table for the README.

    Uses ``pick_sample_row`` to find a representative row (preferring
    Liechtenstein with a ``natural=`` tag) and renders all 13 columns
    as a markdown table with two columns (column, value). Geometry is
    truncated to 100 chars for readability.
    """
    row = pick_sample_row(sample_path)
    if row is None:
        return (
            "*(no sample row available — run `scripts/sample_for_map.py` "
            "to generate `sample/sample_map.jsonl`)*\n"
        )

    # The sample file only has the centroid-only columns (no geometry,
    # no tags list, etc.). To show a complete row in the README we
    # cross-reference the per-country parquet for the picked row's
    # osm_id to fill in the missing columns.
    full_row = _fetch_full_row_from_parquet(out_dir=None, sample_row=row)

    if full_row is None:
        # Fall back to the sample-only columns.
        full_row = row

    cols = [
        ("osm_id", full_row.get("osm_id")),
        ("osm_type", full_row.get("osm_type")),
        ("centroid_lon", full_row.get("centroid_lon")),
        ("centroid_lat", full_row.get("centroid_lat")),
        ("area_km2", full_row.get("area_km2")),
        ("tags", full_row.get("tags")),
        ("matched_tag", full_row.get("matched_tag")),
        ("continent", full_row.get("continent")),
        ("size_bin", full_row.get("size_bin")),
        ("country", full_row.get("country")),
        ("extract_status", full_row.get("extract_status")),
        ("pbf_date", full_row.get("pbf_date")),
        ("geometry_wkt", full_row.get("geometry_wkt")),
    ]
    out = "| column | value |\n|--------|-------|\n"
    for name, value in cols:
        if value is None:
            value_repr = "*(none)*"
        elif name == "area_km2" and isinstance(value, (int, float)):
            value_repr = f"{value:.4f}"
        elif name == "tags" and isinstance(value, list):
            value_repr = "<br>".join(f"`{t}`" for t in value) if value else "*(none)*"
        elif name == "geometry_wkt" and isinstance(value, str):
            value_repr = f"`{_truncate(value, 100)}`"
        elif name in ("centroid_lon", "centroid_lat") and isinstance(value, (int, float)):
            value_repr = f"{value:.6f}"
        else:
            value_repr = f"`{value}`"
        out += f"| {name} | {value_repr} |\n"
    return out


def _fetch_full_row_from_parquet(
    out_dir: Path | None, sample_row: dict
) -> dict | None:
    """Fetch the full row (all 13 columns) for the picked sample row.

    Looks up the row's osm_id in the per-country parquet for its
    country and returns the merged record. Returns ``None`` if the
    parquet is missing or the osm_id isn't found.
    """
    country = sample_row.get("country")
    osm_id = sample_row.get("osm_id")
    if country is None or osm_id is None:
        return None
    parquet = DATASET_DIR / "per_country" / country / f"{country}.parquet"
    if not parquet.is_file():
        # Fallback: flat layout produced before organize_dataset.py ran.
        parquet = DATASET_DIR / f"{country}.parquet"
        if not parquet.is_file():
            return None
    try:
        t = pq.read_table(
            parquet,
            filters=[("osm_id", "=", int(osm_id))],
        )
    except Exception:
        return None
    if t.num_rows == 0:
        return None
    rec = t.to_pylist()[0]
    # The parquet's tags field is list(string) and may come back as
    # a numpy list; coerce to plain list of strings for markdown.
    if rec.get("tags") is not None:
        rec["tags"] = [str(x) for x in rec["tags"]]
    return rec


def _build_size_bin_distribution_table(sample_path: Path) -> str:
    """Build the "Sample size-bin distribution" markdown table.

    Uses ``compute_sample_size_bin_distribution`` to compute counts
    and pct for the sample JSONL, and renders them as a markdown
    table with three columns: size_bin, count, pct.
    """
    dist = compute_sample_size_bin_distribution(sample_path)
    total = sum(c for _, c, _ in dist)
    out = "| size_bin | count | pct |\n|----------|-------|-----|\n"
    for sb, n, pct in dist:
        # Format pct with 1 decimal place.
        out += f"| {sb} | {n:,} | {pct:.1f}% |\n"
    out += f"| **Total** | {total:,} | 100.0% |\n"
    return out


def write_readme(out_dir: Path, countries_done: list[dict], total_polygons: int) -> None:
    """Thin wrapper around the package function.

    Bridges the script's module-level state (PIPELINE_VERSION,
    git_sha, GEOMETRY_ENCODING) into the pure package function.
    """
    from osm_polygon_selection.dataset_build.readme import (
        write_readme as _package_write_readme,
    )
    _package_write_readme(
        out_dir=out_dir,
        countries_done=countries_done,
        total_polygons=total_polygons,
        pipeline_version=PIPELINE_VERSION,
        git_sha_value=git_sha(),
        built_at=datetime.now().isoformat(),
        geometry_encoding=GEOMETRY_ENCODING,
    )


def main() -> None:
    out_dir = DATASET_DIR
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # First pass: countries with a non-empty 03_classified.jsonl.
    # These produce per-country parquet files + manifest rows.
    # IMPORTANT: only consider direct subdirectories of PROC as
    # countries. Per-region subdirectories inside a country (e.g.
    # processed/france/alsace/ from regional processing) are
    # NOT countries — they are subsets of the parent country.
    countries_done: list[dict[str, object]] = []
    for country_dir in sorted(PROC.iterdir()):
        if not country_dir.is_dir():
            continue
        # Skip subdirectories that live inside another country
        # directory. processed/<country>/<region>/... is the regional
        # layout; those are not independent countries.
        if country_dir.parent != PROC:
            continue
        classified = country_dir / "03_classified.jsonl"
        if not classified.exists():
            continue
        country = country_dir.name
        status = extract_status(country)
        pbf_date = pbf_date_for(country)

        rows: list[dict] = []
        # Fast path: stream the JSONL through the optimized writer
        # (O(chunk_size) memory, vectorized matched_tag backfill).
        # Falls back to the per-row Python path only if the writer
        # is unavailable (e.g. import error).
        from osm_polygon_selection.streaming_writer import write_jsonl_to_parquet
        out_file = out_dir / f"{country}.parquet"
        streaming_failed = False
        try:
            n = write_jsonl_to_parquet(
                jsonl_path=classified,
                parquet_path=out_file,
                country=country,
                extract_status=status,
                pbf_date=pbf_date,
                geometry_encoding=GEOMETRY_ENCODING,
                whitelist_path=_RUNTIME_CONFIG.whitelist_path,
            )
        except Exception as e:
            print(f"  {country}: streaming writer failed ({e}); falling back to per-row path")
            streaming_failed = True
            n = 0
        if streaming_failed or n == 0:
            # Either zero-yield or fallback. Try the old path.
            if out_file is not None and out_file.is_file():
                out_file.unlink()
            rows = []
            with classified.open() as f:
                for line in f:
                    rec = row_to_record(json.loads(line), country, status, pbf_date)
                    if rec is not None:
                        rows.append(rec)
            if not rows:
                # Zero-yield 03_classified.jsonl: country attempted, extract ran
                # but produced no polygons (e.g. killed before any output).
                # Record it in the manifest with n_polygons=0 so downstream
                # users know the country was tried but is absent from the data.
                countries_done.append({
                    "country": country,
                    "n_polygons": 0,
                    "extract_status": status,  # "killed" if run.json missing
                    "pbf_date": pbf_date,
                })
                print(f"  {country}: 0 polygons (zero-yield, recorded in manifest only)")
                continue

            table = pa.Table.from_pylist(rows, schema=build_schema())
            out_file = out_dir / f"{country}.parquet"
            pq.write_table(table, out_file, compression="snappy")
            countries_done.append({
                "country": country,
                "n_polygons": len(rows),
                "extract_status": status,
                "pbf_date": pbf_date,
            })
            print(f"  {country}: {len(rows)} polygons -> {out_file.name}")
        else:
            # Streaming path succeeded. Record in manifest.
            countries_done.append({
                "country": country,
                "n_polygons": n,
                "extract_status": status,
                "pbf_date": pbf_date,
            })
            print(f"  {country}: {n} polygons -> {out_file.name} (streaming)")

    # Second pass: countries that have a raw/ PBF but no 03_classified.jsonl
    # at all (i.e. Stage 0 was started but killed before reaching Stage 2/3).
    # Excludes the continent-wide "europe-latest.osm.pbf" (the parent
    # Geofabrik extract, not a country).
    # Also excludes regional sub-PBFs of large countries (e.g. alsace,
    # aquitaine for france) — those are subsets of their parent
    # country, not independent countries.
    raw_dir = HDD / "raw"
    # Regional child slugs come from osm_polygon_selection.dataset_build.countries.

    for pbf in sorted(raw_dir.glob("*-latest.osm.pbf")):
        country = pbf.name.replace("-latest.osm.pbf", "")
        if country == "europe":
            continue
        if is_regional_child(country):
            continue
        if any(c["country"] == country for c in countries_done):
            continue
        countries_done.append({
            "country": country,
            "n_polygons": 0,
            "extract_status": "killed",
            "pbf_date": datetime.fromtimestamp(pbf.stat().st_mtime).strftime("%Y-%m-%d"),
        })
        print(f"  {country}: 0 polygons (no 03 file, PBF present, recorded)")
    print("\nBuilding combined parquet...")
    # Streaming write delegated to the package function (which
    # handles writer close on exception).
    total_rows = _combine_per_country_parquets(
        out_dir=out_dir,
        countries=countries_done,
        output_path=out_dir / "all_world.parquet",
    )
    print(f"  combined: {total_rows} polygons -> {out_dir / 'all_world.parquet'}")

    write_readme(out_dir, countries_done, total_rows)
    write_metadata_yaml(out_dir)

    manifest = {
        "version": PIPELINE_VERSION,
        "git_sha": git_sha(),
        "built_at": datetime.now().isoformat(),
        "total_polygons": total_rows,
        "n_countries": sum(1 for c in countries_done if bool(c["n_polygons"])),
        "countries": countries_done,
        "schema": [f.name for f in build_schema()],
        "filters": {
            "min_area_km2": 0.1,
            "max_area_km2": 100.0,
            "whitelist_size": 22075,
        },
        "resources": {
            "blog_post": "https://noeflandre.com/posts/osm-data-analysis",
            "github_repo": "https://github.com/NoeFlandre/osm-polygon-selection",
            "related_repo": "https://github.com/NoeFlandre/osm-stats",
        },
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"manifest.json written")


if __name__ == "__main__":
    main()
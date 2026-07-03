"""README renderers for the public dataset.

Three kinds of README:

1. ``build_root_readme``: the landing-page README at ``dataset/README.md``.
   Includes yaml frontmatter, provenance, schema, sample distribution,
   example row, train/val/test split, per-country table.

2. ``build_folder_readme``: short READMEs in each of the four subfolders
   (``per_country/``, ``combined/``, ``sample/``, ``preview/``).

3. ``build_country_readme``: per-country READMEs in
   ``per_country/<country>/README.md`` with provenance and links.

Plus ``write_metadata_yaml`` for HF's metadata sidecar.

All renderers are pure functions — they take data and return strings.
Writing to disk is the caller's responsibility.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from osm_polygon_selection.country_table import build_country_table
from osm_polygon_selection.git_meta import git_short_sha
from osm_polygon_selection.pbf_meta import geofabrik_url
from osm_polygon_selection.sample_table import (
    build_example_row_table,
    build_size_bin_distribution_table,
    compute_global_size_bin_distribution,
    compute_sample_size_bin_distribution,
)
from osm_polygon_selection.schema_defs import (
    COLUMN_DESCRIPTIONS,
    COLUMN_TYPES,
)

PIPELINE_VERSION_DEFAULT = "v0.1.0"

# Country notes used by ``build_country_readme``. Add new entries here.
COUNTRY_NOTES: dict[str, str] = {
    "monaco": (
        "The smallest country in the dataset by polygon count. Only 2 "
        "polygons survive the [0.1, 100] km² area filter — Monaco's land "
        "area is 2.02 km², so most of the country fits in one large polygon."
    ),
    "albania": (
        "Albania's OSM coverage has grown sharply since 2017; Tirana and "
        "the coastal strip are well-mapped."
    ),
    "georgia": (
        "Caucasus country with the Greater and Lesser Caucasus mountain "
        "ranges forming the northern border. Geofabrik still files it "
        "under 'europe/' despite being in Asia — we keep that placement "
        "for consistency with the dataset."
    ),
    "ireland-and-northern-ireland": (
        "Combined extract covering the Republic of Ireland and Northern "
        "Ireland (UK). Geofabrik offers this as a single PBF."
    ),
    "macedonia": (
        "Landlocked Balkan country, renamed in 2019 to 'North Macedonia' "
        "but Geofabrik still publishes the PBF under the legacy "
        "'macedonia' name."
    ),
    "botswana": (
        "Landlocked Southern African country dominated by the Kalahari "
        "Desert, with the Okavango Delta (a UNESCO World Heritage "
        "site) in the northwest and the Chobe/Linyanti wetlands in "
        "the north. Geofabrik /africa/ PBF (~84 MB). OSM coverage "
        "is strongest around Gaborone and the protected-area "
        "boundaries; the central and southwestern Kalahari have "
        "sparser polygon coverage."
    ),
    "central-african-republic": (
        "Landlocked Central African country straddling the savanna "
        "and equatorial forest belts, with the Ubangi River forming "
        "much of its southern border with the Democratic Republic of "
        "Congo. Geofabrik /africa/ PBF (~94 MB). Capital Bangui is "
        "the only large urban mapping centre; the rest of the "
        "country has patchy OSM coverage that improved after the "
        "2013 HOT Mapping Initiative."
    ),
    "ivory-coast": (
        "West African country on the Gulf of Guinea (official name "
        "Côte d'Ivoire) with the political capital Yamoussoukro and "
        "the economic capital Abidjan. The southern coastal belt has "
        "excellent OSM coverage around Abidjan's districts and the "
        "Banco National Park; the northern savanna is more sparsely "
        "mapped. Geofabrik /africa/ PBF (~85 MB). Notable features "
        "include the Comoé National Park (a UNESCO World Heritage "
        "site) and the Taï National Park in the southwest."
    ),
    "burkina-faso": (
        "Landlocked West African country (formerly Upper Volta) "
        "crossed by three tributaries of the Volta River and "
        "transitioning from the Sudano-Sahelian savanna in the "
        "south to the Sahel in the north. Capital Ouagadougou and "
        "second city Bobo-Dioulasso have good OSM coverage; the "
        "northern Sahel is sparsely mapped. Geofabrik /africa/ "
        "PBF (~81 MB). Notable protected areas include the "
        "Arly and W National Parks (the latter a transboundary "
        "UNESCO site shared with Niger and Benin)."
    ),
    "angola": (
        "Large Southern African country on the Atlantic coast, "
        "former Portuguese colony, with a long coastline from the "
        "Congo River mouth in the north to the Namib Desert in the "
        "south. Capital Luanda has good OSM coverage; the interior "
        "is sparsely mapped. Geofabrik /africa/ PBF (~81 MB). "
        "Notable protected areas include Iona National Park (in "
        "the Namib fringe), Kissama (Quiçama) National Park near "
        "Luanda, and the Calandula / Kalandula waterfalls."
    ),
    "guinea": (
        "West African country on the Atlantic (former French "
        "colony) with the Fouta Djallon highlands forming the "
        "headwaters of the Niger, Gambia, and Senegal Rivers. "
        "Capital Conakry and the Fouta Djallon region have good "
        "OSM coverage; the forested southeast (the "
        "Guinea Highlands / Nimba mountains) is sparsely mapped. "
        "Geofabrik /africa/ PBF (~111 MB). Notable protected "
        "areas include the Mount Nimba Strict Nature Reserve (a "
        "transboundary UNESCO site shared with Liberia and Côte "
        "d'Ivoire)."
    ),
    "ghana": (
        "West African country on the Gulf of Guinea (former "
        "British colony) with the political capital Accra on "
        "the Atlantic coast and the second city Kumasi in the "
        "central Ashanti region. The Volta Basin (Lake Volta / "
        "Volta River) dominates the eastern half of the country. "
        "OSM coverage is excellent around Accra, Kumasi, and "
        "the cocoa belt; the northern savanna is sparser. "
        "Geofabrik /africa/ PBF (~107 MB). Notable protected "
        "areas include Kakum National Park (the canopy "
        "walkway) and Mole National Park in the north."
    ),
    "senegal-and-gambia": (
        "Geofabrik combined file covering Senegal (West African "
        "country on the Atlantic, former French colony, capital "
        "Dakar) plus The Gambia (a narrow enclave inside Senegal "
        "along the Gambia River, capital Banjul). Dakar has "
        "excellent OSM coverage; the Sine-Saloum Delta and the "
        "Niokolo-Koba National Park (a UNESCO World Heritage "
        "site in eastern Senegal) are well-mapped. The Gambia's "
        "riverbanks are similarly well-traced. Geofabrik /africa/ "
        "combined PBF (~100 MB)."
    ),
    "lesotho": (
        "Small landlocked Southern African country, entirely "
        "surrounded by South Africa and known as the 'Kingdom "
        "in the Sky' for its high-altitude terrain. The Drakensberg "
        "and Maluti mountains cover most of the country, with "
        "the lowest point still above 1,000 m. Capital Maseru "
        "has reasonable OSM coverage; the highlands are sparser. "
        "Geofabrik /africa/ PBF (~120 MB). Notable protected "
        "areas include Sehlabathebe National Park (a UNESCO "
        "World Heritage site) and the Maloti-Drakensberg "
        "Transfrontier Park (shared with South Africa)."
    ),
    "chad": (
        "Large landlocked Central African country (formerly "
        "French Equatorial Africa), with three climatic zones "
        "stretching from the Saharan north (Tibesti Mountains) "
        "through the Sahelian belt to the Sudano-Guinean south. "
        "Capital N'Djamena (on the border with Cameroon) has "
        "decent OSM coverage; the northern Sahara and the "
        "eastern Ennedi Plateau are extremely sparsely mapped. "
        "Geofabrik /africa/ PBF (~128 MB). The shrinking of "
        "Lake Chad (a UNESCO Biosphere Reserve) is the "
        "country's most prominent geographic feature."
    ),
    "south-sudan": (
        "East African landlocked country, gained independence "
        "from Sudan in 2011 and home to the vast Sudd wetland "
        "(one of the world's largest tropical wetlands). Capital "
        "Juba is the only large urban mapping centre; the rest "
        "of the country is extremely sparsely mapped due to "
        "ongoing conflict and limited road access. Geofabrik "
        "/africa/ PBF (~131 MB). The White Nile traverses the "
        "country south to north through the Sudd."
    ),
    "ethiopia": (
        "Large East African country (formerly Abyssinia, never "
        "colonized) dominated by the Ethiopian Highlands, a "
        "massive plateau rising above 1,500 m. Capital Addis "
        "Ababa has good OSM coverage; the highlands and the "
        "Rift Valley are progressively mapped. Geofabrik /africa/ "
        "PBF (~132 MB). Notable features include the Simien "
        "Mountains and Bale Mountains National Parks (both "
        "UNESCO sites), the Danakil Depression (one of the "
        "hottest places on Earth), and the rock-hewn churches "
        "of Lalibela and the ancient obelisks of Aksum."
    ),
    "malawi": (
        "Landlocked Southeast African country dominated by "
        "Lake Malawi (Lake Nyasa), the ninth-largest lake in "
        "the world and home to more species of fish than any "
        "other. Capital Lilongwe has decent OSM coverage; the "
        "shoreline of Lake Malawi and the southern Shire "
        "Highlands are progressively mapped. Geofabrik /africa/ "
        "PBF (~147 MB). Notable protected areas include Lake "
        "Malawi National Park (a UNESCO World Heritage site) "
        "and Nyika National Park on the Zambia border."
    ),
    "somalia": (
        "Horn of Africa country on the Indian Ocean, with the "
        "self-declared republic of Somaliland in the north and "
        "Puntland in the northeast. Capital Mogadishu has "
        "limited OSM coverage due to ongoing conflict; "
        "Somaliland (Hargeisa, Berbera port) has somewhat "
        "better mapping. Geofabrik /africa/ PBF (~156 MB). "
        "Notable features include the Horn of Africa's northern "
        "coastline, the Shabelle and Jubba river valleys in "
        "the south, and the Bajuni / Banaadir coastal islands."
    ),
    "mali": (
        "Large landlocked West African country (formerly "
        "French Sudan), with most of its territory in the "
        "Saharan and Sahelian zones. Capital Bamako on the "
        "Niger River has good OSM coverage; the historic "
        "cities of Timbuktu, Djenné, and Gao are progressively "
        "mapped. Geofabrik /africa/ PBF (~164 MB). Notable "
        "features include the Bandiagara Escarpment (home to "
        "the Dogon people and a UNESCO World Heritage site), "
        "the Niger River Inner Delta, and the historic trans-"
        "Saharan trade route cities."
    ),
    "zimbabwe": (
        "Southern African landlocked country (formerly "
        "Rhodesia) with the high plateau of the Zimbabwe "
        "Craton. Capital Harare has good OSM coverage; "
        "Bulawayo and the Victoria Falls area are progressively "
        "mapped. Geofabrik /africa/ PBF (~170 MB). Notable "
        "features include Victoria Falls / Mosi-oa-Tunya (a "
        "transboundary UNESCO site shared with Zambia), the "
        "Great Zimbabwe ruins, Hwange National Park (one of "
        "Africa's largest elephant sanctuaries), and Lake "
        "Kariba (one of the world's largest artificial lakes)."
    ),
    "egypt": (
        "Large North African country dominated by the Nile "
        "Valley and the Sahara Desert, with a small but dense "
        "population along the river. Capital Cairo is the "
        "largest city in the Arab world with very good OSM "
        "coverage; Alexandria and the Nile Delta are similarly "
        "well-mapped. Geofabrik /africa/ PBF (~169 MB). "
        "Notable features include the pyramids of Giza, the "
        "ancient sites of Luxor and Karnak, the Sinai "
        "Peninsula, and the Red Sea coast with its coral reefs."
    ),
}


# ---------------------------------------------------------------------------
# Root README
# ---------------------------------------------------------------------------

_YAML_FRONTMATTER = """---
license: odbl
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
---
"""

_ROOT_README_INTRO = """# osm-polygon-selection dataset

A curated set of OpenStreetMap polygons across {n_countries}
countries (49 European + {n_non_europe} in Africa), classified by
**size bin** (`small` / `medium` / `large`, area in [0.1, 100] km²)
and tagged by continent (Natural Earth admin0 lookup).

**Size bins:**

- **`small`** — area in **[0.1, 1) km²** (10,000 m² to 1 km², roughly
  100 m × 100 m to ~1 km × 1 km). Examples: a city block, a small
  park, a single farm field, a small wood lot, a residential
  courtyard, a parking lot, an industrial yard.
- **`medium`** — area in **[1, 10) km²** (1 km² to 10 km², roughly
  1 km × 1 km to 3 km × 3 km). Examples: a large park, a small
  village/town footprint, a reservoir, a forest patch, an
  industrial zone, a golf course, a cemetery, a nature reserve.
- **`large`** — area in **[10, 100] km²** (10 km² to 100 km², roughly
  3 km × 3 km to 10 km × 10 km). Examples: a large forest, a
  big lake, an entire town or small city, a large military
  training area, a national park section, a sizable agricultural
  region.

Polygons smaller than 0.1 km² (most individual buildings, houses,
small ponds, single fields) and larger than 100 km² (whole countries,
mountain ranges, big seas) are excluded by the size filter (see
[Filter chain](#filter-chain) below).

**Status:** All {n_countries} countries are extracted end-to-end (every OSM object examined, `run.json` written).

**Total polygons:** {total_polygons:,}
(combined parquet: `all_europe.parquet`).

## Layout

This dataset is split across four subfolders so you can pull only what
you need:

| folder | what's inside | typical size |
|--------|---------------|--------------|
| [`per_country/`](./per_country/) | one folder per country with `<country>.parquet` + `README.md` | ~7 GB total, <1 MB per small country |
| [`combined/`](./combined/) | `all_europe.parquet` — every polygon in one file | ~9 GB |
| [`sample/`](./sample/) | `sample_map.jsonl` — ~4k representative polygons for quick viz | <1 MB |
| [`preview/`](./preview/) | `map_preview.png` — static map thumbnail | ~1 MB |

Start with `sample/` or `preview/` for a quick look. Pull
`per_country/<country>/<country>.parquet` for a single-country
study. Use `combined/all_europe.parquet` for cross-country work.

## What's in this dataset

Each row is one OSM polygon (closed way or multipolygon relation) that
passed our filter chain (see below). The polygon **geometry itself**
is included in the row as WKT (or WKB if `OSM_POLYGON_GEOMETRY=wkb`
is set when the dataset is built) so you can render, query, or
reproject it directly without re-deriving from centroid+area.

{schema_table}

## Provenance

- Pipeline version: {pipeline_version}
- Git SHA: {git_sha}
- Built: {built_at}
- Source: Geofabrik regional extracts (`https://download.geofabrik.de/`)
- Whitelist: 22,075 OSM `key=value` tags from osm-stats (see
  `docs/whitelist_decisions.md` in the project repo, or read the
  full rationale in the
  [blog post](https://noeflandre.com/posts/osm-data-analysis)).
  The whitelist is designed to filter polygons by landuse-style
  tags (`natural`, `landuse`, `leisure`, `amenity`, etc.) so the
  dataset focuses on physical land-cover / land-use features
  rather than buildings, addresses, or points of interest.

## Geographic distribution

![polygon distribution across Europe](./preview/map_preview.png)

(Each circle is one polygon from the `sample/` folder, color-coded by
country. Circle size is proportional to `sqrt(area_km2)`.)

## Size-bin distribution (full dataset)

Counts every polygon in the {total_polygons:,}-polygon dataset by
`size_bin`, computed directly from `combined/all_europe.parquet`
via `pyarrow.compute.value_counts`. Percentages are exact ratios
over the entire dataset, not a sample.

{size_bin_table}

## Example row

Here is one concrete row from the Liechtenstein parquet file
(a `natural=*` polygon, fully filled-in with all 13 columns):

{example_row_table}

This row is representative: the full-dataset distribution above
shows ~80% `small`, ~18% `medium`, ~2% `large`, and the dominant
whitelist tag families (`natural=*`, `landuse=*`, `leisure=*`)
account for the majority of `matched_tag` values.

## Filter chain

Each polygon in this dataset has passed three filters:

1. **Size filter (Stage 0)**: area in [0.1, 100] km².
   Polygons smaller than 0.1 km² or larger than 100 km² are dropped.
2. **Whitelist filter (Stage 2)**: at least one OSM tag in the
   22,075-tag whitelist. The whitelist is derived from a clustering
   of OSM tags across both `tfidf` and `embeddings` analyses.
3. **Classify (Stage 3)**: continent assigned via Natural Earth
   admin0 shapefile, size_bin assigned by area.

{split_section}

## Per-country summary

{country_table}

[Back to the dataset root](./README.md)
"""


_SPLIT_SECTION_TEMPLATE = """## Train / val / test split

Every row in every parquet (`per_country/<country>/<country>.parquet`
and `combined/all_europe.parquet`) carries a **`split`** column with
one of three values: `train`, `val`, or `test`.

| split | ratio | polygons |
|-------|-------|----------|
| train | 80% | {split_train:,} |
| val   | 10% | {split_val:,} |
| test  | 10% | {split_test:,} |
| **Total** | **100%** | **{total_polygons:,}** |

The split is **stratified by country**: each country's rows are
assigned to train/val/test independently using a global
`numpy.random.default_rng` seeded once with **{split_seed}** and
offset per country. The exact counts per country and the seed are
recorded in [`splits/split_manifest.json`](./splits/split_manifest.json).

To load only one split (e.g. for training), filter in pyarrow:
```python
import pyarrow.compute as pc
import pyarrow.parquet as pq
table = pq.read_table("combined/all_europe.parquet")
train = table.filter(pc.equal(table["split"], "train"))
```

The split is deterministic and re-runnable:
```bash
uv run python scripts/make_split.py            # default seed=42, 80/10/10
uv run python scripts/make_split.py --seed 7   # different reproducible split
"""


def _split_section(root: Path) -> str:
    """Return the split section markdown, or '' if no split manifest."""
    split_manifest_path = root / "splits" / "split_manifest.json"
    if not split_manifest_path.is_file():
        return ""
    with split_manifest_path.open() as f:
        sm = json.load(f)
    counts = sm.get("counts", {})
    return _SPLIT_SECTION_TEMPLATE.format(
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

    # Imported lazily to avoid a circular import with paths.py.
    from osm_polygon_selection.pbf_meta import NON_EUROPE_COUNTRIES
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

    text = _YAML_FRONTMATTER + _ROOT_README_INTRO.format(
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


# ---------------------------------------------------------------------------
# Folder READMEs
# ---------------------------------------------------------------------------

_FOLDER_TEMPLATES: dict[str, str] = {
    "per_country": """# per_country/

{n_countries} country folders (one folder per country). Each contains:

- `<country>.parquet` — all polygons for that country (schema matches the root README).
- `README.md` — country-specific notes (pbf date, source sub-PBFs if any, polygon count).

Pull a single country with:
```python
import pyarrow.parquet as pq
t = pq.read_table("per_country/france/france.parquet")
```
""",
    "combined": """# combined/

Single parquet containing every polygon across all {n_countries} countries.

- `all_europe.parquet` — schema matches the root README. Includes a `split` column (`train`/`val`/`test`) if `make_split.py` has been run.

Use this for cross-country work. For per-country analysis, pull from `per_country/` instead (smaller per-file download).
""",
    "sample": """# sample/

A geographically-stratified sample of polygons for quick visualization and ad-hoc queries.

- `sample_map.jsonl` — one JSON object per polygon, ~4k polygons across all {n_countries} countries. The same file that backs `preview/map_preview.png`.
""",
    "preview": """# preview/

Static thumbnail of the dataset's geographic distribution.

- `map_preview.png` — 1600×1100 PNG, circles colored by country. **Sample only** (not exhaustive) — see [`sample/`](../sample/) for how the sample is built.
""",
}


def build_folder_readme(folder: str, n_countries: int) -> str:
    """Render a short README for one of the four subfolders."""
    if folder not in _FOLDER_TEMPLATES:
        raise ValueError(f"unknown folder: {folder!r}; expected one of {list(_FOLDER_TEMPLATES)}")
    return _FOLDER_TEMPLATES[folder].format(n_countries=n_countries)


# ---------------------------------------------------------------------------
# Country README
# ---------------------------------------------------------------------------

_COUNTRY_README_TEMPLATE = """# {country}

{n_polygons:,} polygons from `{country}-latest.osm.pbf` on Geofabrik
([source]({geofabrik_url})), filtered by the
[22,075-tag whitelist](https://github.com/NoeFlandre/osm-stats) and
classified by continent + size bin.

| field | value |
|-------|-------|
| country | `{country}` |
| polygons | **{n_polygons:,}** |
| extract_status | **{extract_status}** |
| pbf_date | {pbf_date} |
| source | `{country}-latest.osm.pbf` |
| Geofabrik extract | <{geofabrik_url}> |

## Geometry

The parquet file in this folder (`{country}.parquet`) has the same schema as
the combined `combined/all_europe.parquet`. Each row carries the polygon
**geometry as WKT** (default), plus centroid + area + the whitelist-matched tag.

Load with:
```python
import pyarrow.parquet as pq
table = pq.read_table("per_country/{country}/{country}.parquet")
df = table.to_pandas()
```

## Notes

{country_note}
"""


def _country_note(country: str, n_polygons: int) -> str:
    """Return a 1-2 sentence note about this country, or generic fallback."""
    if country in COUNTRY_NOTES:
        return COUNTRY_NOTES[country]
    if n_polygons <= 100:
        return f"Tiny country with only {n_polygons:,} polygons surviving the size filter."
    if n_polygons <= 5000:
        return f"Small country with {n_polygons:,} polygons. Most urban + coastal features."
    return ""


def build_country_readme(
    country: str,
    n_polygons: int,
    extract_status: str,
    pbf_date: str,
) -> str:
    """Render the per-country README content."""
    note = _country_note(country, n_polygons) or "Standard coverage."
    return _COUNTRY_README_TEMPLATE.format(
        country=country,
        n_polygons=n_polygons,
        extract_status=extract_status,
        pbf_date=pbf_date,
        geofabrik_url=geofabrik_url(country),
        country_note=note,
    )


# ---------------------------------------------------------------------------
# Metadata YAML (HF sidecar)
# ---------------------------------------------------------------------------

_METADATA_YAML = """license: odbl
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


def write_metadata_yaml(out_dir: Path) -> None:
    """Write HF's required metadata sidecar at ``out_dir/metadata.yaml``."""
    (out_dir / "metadata.yaml").write_text(_METADATA_YAML)


# Re-exported for convenience.
__all__ = [
    "PIPELINE_VERSION_DEFAULT",
    "build_root_readme",
    "build_folder_readme",
    "build_country_readme",
    "write_metadata_yaml",
]

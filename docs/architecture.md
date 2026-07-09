# Architecture

High-level overview of the build pipeline, module ownership, and
the rules for adding code or tests. The companion document
[`AGENT_HANDOFF.md`](./internal/AGENT_HANDOFF.md) captures project
conventions; this one focuses on the **structure** of the
package.

## Pipeline stages

```
[Geofabrik PBF] -> stage0 -> stage2 -> stage3 -> [03_classified.jsonl]
                                                              |
                                                              v
                       build_dataset -> [per-country parquet + combined parquet
                                          + manifest.json + README.md]
                                                              |
                                                              v
                   organize_dataset -> [per_country/<c>/, combined/, sample/,
                                         preview/, splits/, root README.md,
                                         metadata.yaml]
                                                              |
                                                              v
                                       sample_for_map -> [sample/sample_map.jsonl]
                                                              |
                                                              v
                                              make_split -> [combined/all_world.parquet
                                                              with split column]
                                                              |
                                                              v
                                        upload_to_hf -> [HuggingFace dataset]
```

Each stage has a script in `scripts/` (CLI only) and a package
in `src/osm_polygon_selection/`.

## Where generated READMEs come from

All README text is **owned by the `readme` package** and called
from elsewhere. No other package or script duplicates the
templates.

```
readme.templates
  -> YAML_FRONTMATTER, ROOT_README_INTRO, SPLIT_SECTION_TEMPLATE,
     FOLDER_TEMPLATES, COUNTRY_README_TEMPLATE, METADATA_YAML,
     DATASET_README_BODY
  -> long-form markdown / YAML constants, isolated here so the
     renderer modules stay small (~30-150 LOC each)

readme.root.build_root_readme       -> organize_dataset root README
readme.dataset.write_readme         -> build_dataset root README
                                       (the "pre-organize" form)
readme.country.build_country_readme -> per_country/<c>/README.md
readme.folder.build_folder_readme   -> per_country/, combined/,
                                       sample/, preview/ READMEs
readme.metadata.write_metadata_yaml -> metadata.yaml
readme.notes.country_note           -> curated country blurb

readme_render.py (legacy)           -> re-exports the above for
                                       backwards-compat
```

## Where runtime paths come from

```
paths.dataset_root()           # OSM_DATASET_DIR or sibling-of-repo
runtime_config.RuntimeConfig   # env-driven HDD / PROC / whitelist
                                 paths (honors $OSM_DATA_ROOT)
```

Both are env-driven. See `docs/internal/AGENT_HANDOFF.md` section 1 for
the storage policy that decides which env vars must be set
before running any pipeline.

## How to safely add tests

1. Pick the right `tests/<domain>/` subfolder. The rule is one
   test module per source module. The list in
   `AGENT_HANDOFF.md` section 10 (Test tree ownership) is the
   canonical mapping.
2. If the test pins a behavior that could change in a future
   refactor, use a **byte-exact fixture** in
   `tests/fixtures/<domain>/`. A frozen fixture makes a
   regression immediately visible.
3. If the test pins **orchestration** (which functions get
   called, in what order, on what inputs), use a **characterization
   test** that calls the package function directly with a
   synthetic input.
4. Avoid `importlib.util.spec_from_file_location(...)` for tests
   that exercise domain behavior. Import the package module
   directly. Keep script-level tests (`scripts/<name>.py`) for
   CLI / env-parsing behavior only.

## What NOT to mutate in tests

- **Don't** rewrite the canonical parquet schema. If you need
  a new column, add it in `schema_defs.build_schema` first;
  the test then picks up the new schema automatically.
- **Don't** modify the runner's `iter_classified_country_dirs`
  / `discover_killed_pbf_countries` output order. The combined
  parquet is built in `manifest` order which is
  `sorted(PROC.iterdir())`; changing the sort order changes
  the per-row `split` assignment downstream.
- **Don't** delete or rename files in `tests/fixtures/readme/`
  without regenerating the fixture via
  `uv run python tests/fixtures/readme/_generator.py`. The
  byte-exact tests will fail otherwise.
- **Don't** write tests that depend on `/Volumes/Seagate M3/`.
  All tests must be hermetic (use `tmp_path`).

## Module ownership map

See [`AGENT_HANDOFF.md` section 10](./internal/AGENT_HANDOFF.md#10-verification-module-ownership-and-rules-post-quality-uplift)
for the full table of which package owns which concern.

Quick summary:

| Concern                  | Package                            |
|--------------------------|------------------------------------|
| Build orchestration      | `dataset_build.runner`             |
| Build per-country write  | `dataset_build.country_processing` |
| Build discovery          | `dataset_build.discovery`          |
| Build whitelist cache    | `dataset_build.whitelist`          |
| Build artifacts          | `dataset_build.artifacts`          |
| Organize orchestration   | `dataset_organize.runner`          |
| Organize READMEs         | `dataset_organize.readmes`         |
| Organize manifests       | `dataset_organize.manifests`       |
| All README renderers     | `readme`                           |
| Long-form README text    | `readme.templates`                 |
| Sample-for-map sampling  | `sampling`                         |
| Streaming JSONL writer   | `parquet_write` (facade: `streaming_writer`) |
| Train/val/test split     | `dataset_split`                    |
| Sample-table renderers   | `sample_tables` (facade: `sample_table`) |
| Stage 0/2/3              | `stages` (stage 0 split into `stages.extract_stage`) |
| PBF metadata             | `pbf_meta`                         |
| Curated country notes    | `country_notes`                    |

## Canonical import paths

Each domain owns a subpackage. **Domain packages import from
their canonical locations, never from a root-level facade.**
Root-level facades exist only for backwards-compat with existing
importers; new code should not depend on them.

| Concern                  | Canonical import                          | Backwards-compat facade |
|--------------------------|-------------------------------------------|-------------------------|
| PBF metadata             | `osm_polygon_selection.pbf_meta`          | `osm_polygon_selection.pbf_meta` (was a single file) |
| Regional sub-PBF map     | `osm_polygon_selection.pbf_meta.regional` | `osm_polygon_selection.regional_pbf_meta` |
| Curated country notes    | `osm_polygon_selection.country_notes`     | (was a single file `country_notes.py`) |
| Train/val/test split     | `osm_polygon_selection.dataset_split`     | `scripts.make_split` (re-exports `_add_split_column_streaming` / `_write_combined_streaming`) |
| Sample-table renderers   | `osm_polygon_selection.sample_tables`     | `osm_polygon_selection.sample_table` |
| Streaming JSONL writer   | `osm_polygon_selection.parquet_write`     | `osm_polygon_selection.streaming_writer` |
| Stage 0 extract          | `osm_polygon_selection.stages.extract_stage` | `osm_polygon_selection.stages.extract` |
| README renderers         | `osm_polygon_selection.readme`            | `osm_polygon_selection.readme_render` |
| Config / runtime paths   | `osm_polygon_selection.runtime_config`, `osm_polygon_selection.paths` | (root modules) |

If you add a new domain module, prefer creating a subpackage
rather than adding to `src/osm_polygon_selection/<name>.py`.

## Compatibility facades at the src root

Several root-level modules are **thin compatibility facades**
that re-export symbols from a subpackage. They exist so existing
imports (`from osm_polygon_selection.<name> import ...`) keep
working after a refactor splits the module into a subpackage.

Current facades (root-level module → canonical subpackage):

- `streaming_writer.py` → `parquet_write/`
- `sample_table.py` → `sample_tables/`
- `readme_render.py` → `readme/`
- `regional_pbf_meta.py` → `pbf_meta/regional`

When you delete a facade, run the test suite first to surface
all callers; the canonical subpackage is the only stable
import path going forward.

## Scripts: public CLI vs internal operation

The `scripts/` directory contains two tiers:

| Path                          | Audience    | Notes |
|-------------------------------|-------------|-------|
| `scripts/stage0_extract.py` … `scripts/upload_to_hf.py` | Public | One CLI per pipeline stage. Thin wrappers; no domain logic. |
| `scripts/sample_for_map.py`   | Public      | Grid-stratified sample. |
| `scripts/visualize.py`        | Public      | JSONL → interactive folium map. |
| `scripts/operations/*.py`     | Maintainer  | HDD-only operations (legacy loop driver, sub-region batch, screenshot capture, one-country shortcut). |
| `scripts/operations/*.sh`    | Maintainer  | Shell shortcuts. Honor `$OSM_DATA_ROOT`. |

Public scripts must be **thin**: parse argv, call a package
`runner.run_*`, print results. No business logic in the script
itself. Internal/operational scripts (`scripts/operations/`) may
have hard-coded maintainer paths that are `$OSM_DATA_ROOT`-
overridable.

## Generated docs and templates

All README / metadata YAML text lives in `readme.templates`
(659 LOC of pure template constants). Renderer modules
(`readme.root`, `readme.folder`, `readme.country`,
`readme.dataset`, `readme.metadata`) are short (~30-150 LOC)
and delegate prose to the templates module. Tests under
`tests/readme/` pin the byte-exact README fixtures; if you
change prose in `readme.templates`, regenerate the fixtures.

## Adding a new script without root sprawl

1. If the script is a public CLI for a new pipeline stage,
   put it at `scripts/<name>.py`. Make sure its body is a thin
   wrapper around a package function.
2. If the script is a maintainer-only operational tool (sub-region
   batch, one-country shortcut, screenshot capture), put it at
   `scripts/operations/<name>.py` or `scripts/operations/<name>.sh`.
3. If the script needs hard-coded local paths, route them through
   `$OSM_REPO_ROOT`, `$OSM_DATA_ROOT`, `$OSM_DATASET_DIR`, or
   `RuntimeConfig` — never machine-specific absolute home-directory
   paths.
4. Add a smoke test under `tests/scripts/` that only checks
   argparse + module import. Don't write tests that depend on
   a real PBF, browser, or HF token.
5. If the public docs reference the script, update
   `docs/architecture.md` (this file) and `README.md`'s
   Repository layout.

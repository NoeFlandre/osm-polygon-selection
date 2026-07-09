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
| Build legacy script shims | `dataset_build.script_compat`     |
| Organize orchestration   | `dataset_organize.runner`          |
| Organize READMEs         | `dataset_organize.readmes`         |
| Organize manifests       | `dataset_organize.manifests`       |
| All README renderers     | `readme`                           |
| Per-country markdown table | `readme.tables`                  |
| Long-form README text    | `readme.templates`                 |
| Sample-for-map sampling  | `sampling`                         |
| Streaming JSONL writer   | `parquet_write`                    |
| Train/val/test split     | `dataset_split`                    |
| Sample-table renderers   | `sample_tables`                    |
| Stage 0/2/3              | `stages` (stage 0 split into `stages.extract_stage`) |
| PBF metadata             | `pbf_meta`                         |
| Curated country notes    | `country_notes`                    |
| Schema definitions       | `schema`                           |
| Visualization (folium)   | `visualization`                    |
| HF dataset upload        | `hf_upload`                        |
| Runtime config           | `config`                           |
| Project + dataset paths  | `config.paths`                     |
| Git SHA / repo root      | `config.git`                       |
| Dataset folder layout    | `dataset_layout`                   |
| Whitelist I/O + matched_tag | `io.whitelist`                  |
| PyArrow compat shims     | `io.pyarrow_compat`                |
| Extract status check     | `stages.status`                    |
| Maintainer operations    | `operations` (downloads, subprocesses, europe_loop, regions, screenshot, cli) |
| Per-script CLI entry points | `cli.<name>`                    |
| Legacy import aliases    | `compat`                           |

## Canonical import paths

Each domain owns a subpackage. **Domain packages import from
their canonical locations, never from a root-level facade.**
The root-level aliases exist only for backwards-compat with
existing importers; new code should not depend on them.

The complete list of legacy root-level paths and their
canonical targets is in the [Compatibility imports](#compatibility-imports)
section above.

If you add a new domain module, prefer creating a subpackage
rather than adding to `src/osm_polygon_selection/<name>.py`.

## Compatibility imports

The package root (`src/osm_polygon_selection/`) contains exactly
**one** Python file: `__init__.py`. Every other public concern
lives in a subpackage.

Legacy import paths such as
``from osm_polygon_selection.country_table import build_country_table``
keep working through a `sys.modules` alias installed at package
import time (see
:mod:`osm_polygon_selection.compat.import_aliases`). Each
alias maps a legacy root-level name to its canonical subpackage:

| Legacy path | Canonical subpackage |
|-------------|----------------------|
| `osm_polygon_selection.country_table` | `osm_polygon_selection.readme.tables` |
| `osm_polygon_selection.extract_status` | `osm_polygon_selection.stages.status` |
| `osm_polygon_selection.git_meta` | `osm_polygon_selection.config.git` |
| `osm_polygon_selection.paths` | `osm_polygon_selection.config.paths` |
| `osm_polygon_selection.pyarrow_compat` | `osm_polygon_selection.io.pyarrow_compat` |
| `osm_polygon_selection.runtime_config` | `osm_polygon_selection.config.runtime` |
| `osm_polygon_selection.whitelist_io` | `osm_polygon_selection.io.whitelist` |
| `osm_polygon_selection.schema_defs` | `osm_polygon_selection.schema` |
| `osm_polygon_selection.sample_table` | `osm_polygon_selection.sample_tables` |
| `osm_polygon_selection.readme_render` | `osm_polygon_selection.readme` |
| `osm_polygon_selection.regional_pbf_meta` | `osm_polygon_selection.pbf_meta.regional` |
| `osm_polygon_selection.streaming_writer` | `osm_polygon_selection.parquet_write.runner` |

The list of legacy aliases is the **single source of truth** in
`osm_polygon_selection.compat.import_aliases.LEGACY_ALIASES`.

## Scripts: public CLI vs internal operation

The `scripts/` directory is organized into subfolders by concern.
Each subfolder holds the canonical executable scripts; the
root-level `scripts/*.py` files are thin backwards-compat
launchers that call into the canonical script via
`runpy.run_path` (or re-execute the canonical source in the
root module's namespace for tests that mutate module globals).

| Path | Audience | Notes |
|------|----------|-------|
| `scripts/pipeline/stage0_extract.py` … `stage3_classify.py` | Public | One CLI per pipeline stage. |
| `scripts/dataset/build_dataset.py` | Public | PBF -> per-country parquet + README. |
| `scripts/dataset/organize_dataset.py` | Public | Move files into the canonical layout. |
| `scripts/dataset/make_split.py` | Public | Deterministic train/val/test split. |
| `scripts/dataset/split_parquets.py` | Public | Per-split parquet files for HF viewer. |
| `scripts/dataset/sample_for_map.py` | Public | Small sample for folium preview. |
| `scripts/publishing/upload_to_hf.py` | Public | Upload to HuggingFace. |
| `scripts/preview/visualize.py` | Public | Render the folium preview map. |
| `scripts/operations/*.py` | Maintainer | HDD-only operator tools. |
| `scripts/operations/*.sh` | Maintainer | Shell shortcuts. |
| `scripts/*.py` (root) | Public | Backwards-compat launchers (~10-13 LOC). |

Public scripts must be **thin**: parse argv, call a package
`runner.run_*` or `cli.<name>.main`, print results. No business
logic in the script itself. The root-level
`scripts/<name>.py` files exist so old
``uv run scripts/<name>.py`` invocations keep working; new code
should use the canonical subfolder paths.

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

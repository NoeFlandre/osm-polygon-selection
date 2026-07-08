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
| Stage 0/2/3              | `stages`                           |

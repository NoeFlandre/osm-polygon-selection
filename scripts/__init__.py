"""Scripts package.

Subfolders:
- ``scripts/pipeline`` — stage0/1/2/3 (PBF -> JSONL).
- ``scripts/dataset`` — build, organize, make_split, sample_for_map, split_parquets.
- ``scripts/publishing`` — upload_to_hf.
- ``scripts/preview`` — visualize (folium map).
- ``scripts/operations`` — operator tools (maintainer-only).

The root-level ``scripts/*.py`` files are backwards-compat
launchers that ``runpy.run_path`` the canonical script in the
matching subfolder. They exist so old ``uv run scripts/<name>.py``
invocations keep working.
"""

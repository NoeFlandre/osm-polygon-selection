"""Inventory + structural rules for root-level src modules.

The root of ``src/osm_polygon_selection/`` should contain only:

- ``__init__.py`` (package marker + alias installer),
- subpackages.

There are no backwards-compat facade ``.py`` files at the root:
legacy import paths are redirected to their canonical subpackages
via the ``sys.modules`` aliases installed in
:mod:`osm_polygon_selection.compat.import_aliases`.

This test enforces:

- only ``__init__.py`` exists as a root ``.py``,
- no module/package name collisions,
- legacy import paths still resolve (covered separately by
  ``tests/metadata/test_public_imports.py``).
"""

from __future__ import annotations

from pathlib import Path

import pytest


SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "osm_polygon_selection"

# The only .py file allowed at the root: the package marker.
# It must contain only an alias-installation call (no business
# logic, no real re-exports).
ROOT_ALLOWED_FILES = {
    "__init__.py",
}

# Legacy import paths that must still resolve via the alias
# mechanism in osm_polygon_selection.compat.import_aliases.
# There are no .py files for these at the root; the alias makes
# ``import osm_polygon_selection.<old>`` return the canonical
# module.
ROOT_LEGACY_ALIASES = {
    "country_table": "readme.tables",
    "extract_status": "stages.status",
    "git_meta": "config.git",
    "paths": "config.paths",
    "pyarrow_compat": "io.pyarrow_compat",
    "regional_pbf_meta": "pbf_meta.regional",
    "runtime_config": "config.runtime",
    "sample_table": "sample_tables",
    "readme_render": "readme",
    "schema_defs": "schema",
    "streaming_writer": "parquet_write.runner",
    "whitelist_io": "io.whitelist",
}


def _list_root_modules() -> list[Path]:
    return sorted(p for p in SRC_ROOT.glob("*.py") if p.is_file())


class TestRootSrcInventory:
    def test_root_contains_only_init(self) -> None:
        """Only ``__init__.py`` may live at the root. No facades."""
        files = {p.name for p in _list_root_modules()}
        extra = files - ROOT_ALLOWED_FILES
        assert not extra, (
            f"unexpected root-level .py files: {sorted(extra)}. "
            f"Delete them. Legacy import paths are resolved via "
            f"sys.modules aliases (see osm_polygon_selection.compat.import_aliases)."
        )

    @pytest.mark.parametrize("alias_name", sorted(ROOT_LEGACY_ALIASES))
    def test_legacy_alias_resolves(self, alias_name: str) -> None:
        """Each legacy root-level import path must still work."""
        import importlib
        # Import the parent package first to install the aliases.
        importlib.import_module("osm_polygon_selection")
        mod = importlib.import_module(f"osm_polygon_selection.{alias_name}")
        assert mod is not None

    def test_no_module_package_name_collisions(self) -> None:
        """No root ``<name>.py`` may coexist with ``<name>/`` package.

        Python's import machinery gives the package priority and
        the file becomes shadowed (a confusing source of bugs).
        """
        files = {p.stem for p in _list_root_modules()}
        dirs = {p.name for p in SRC_ROOT.iterdir() if p.is_dir()}
        collisions = sorted(files & dirs - {"__pycache__"})
        assert not collisions, (
            f"root-level module/package name collisions: {collisions}."
        )


def test_root_inventory_classification() -> None:
    """Classify each root module for the inventory report."""
    classification: dict[str, str] = {}
    for p in _list_root_modules():
        if p.name in ROOT_ALLOWED_FILES:
            classification[p.name] = "package init"
        else:
            classification[p.name] = "UNCLASSIFIED"
    assert "UNCLASSIFIED" not in classification.values(), (
        f"unclassified root modules: "
        f"{[k for k, v in classification.items() if v == 'UNCLASSIFIED']}"
    )

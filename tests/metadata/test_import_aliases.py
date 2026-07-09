"""Tests for the compat.import_aliases module."""

from __future__ import annotations

import sys

import pytest


class TestInstallSysModulesAliases:
    def test_legacy_paths_in_sys_modules(self) -> None:
        """After import, all legacy aliases are in ``sys.modules``."""
        import osm_polygon_selection
        for legacy in (
            "osm_polygon_selection.country_table",
            "osm_polygon_selection.extract_status",
            "osm_polygon_selection.git_meta",
            "osm_polygon_selection.paths",
            "osm_polygon_selection.pyarrow_compat",
            "osm_polygon_selection.runtime_config",
            "osm_polygon_selection.whitelist_io",
            "osm_polygon_selection.schema_defs",
            "osm_polygon_selection.sample_table",
            "osm_polygon_selection.readme_render",
            "osm_polygon_selection.regional_pbf_meta",
            "osm_polygon_selection.streaming_writer",
        ):
            assert legacy in sys.modules, (
                f"{legacy} not in sys.modules after import"
            )

    def test_aliases_point_to_canonical(self) -> None:
        """Each alias resolves to its canonical subpackage."""
        import osm_polygon_selection
        from osm_polygon_selection.compat.import_aliases import LEGACY_ALIASES
        for old, canonical in LEGACY_ALIASES.items():
            alias_module = sys.modules[f"osm_polygon_selection.{old}"]
            # The alias module's name should be the canonical name.
            assert alias_module.__name__ == canonical, (
                f"osm_polygon_selection.{old} alias points to "
                f"{alias_module.__name__}, expected {canonical}"
            )

    def test_install_is_idempotent(self) -> None:
        """Running the installer twice is a no-op."""
        from osm_polygon_selection.compat.import_aliases import (
            install_sys_modules_aliases,
        )
        # Pre-populate one entry to simulate a pre-existing entry.
        from osm_polygon_selection.compat.import_aliases import LEGACY_ALIASES
        first_old = next(iter(LEGACY_ALIASES))
        sentinel = object()
        sys.modules[f"osm_polygon_selection.{first_old}"] = sentinel  # type: ignore[assignment]
        install_sys_modules_aliases()
        # The sentinel should still be there (not clobbered).
        assert (
            sys.modules[f"osm_polygon_selection.{first_old}"] is sentinel  # type: ignore[comparison-overlap]
        )
        # Restore.
        import osm_polygon_selection  # noqa: F401
        del sys.modules[f"osm_polygon_selection.{first_old}"]
        install_sys_modules_aliases()


class TestLegacyAliases:
    def test_country_table_aliases_to_readme_tables(self) -> None:
        import osm_polygon_selection.country_table as ct
        from osm_polygon_selection.readme.tables import (
            build_country_table as canonical,
        )
        assert ct.build_country_table is canonical

    def test_extract_status_aliases_to_stages_status(self) -> None:
        import osm_polygon_selection.extract_status as es
        from osm_polygon_selection.stages.status import (
            extract_status as canonical,
        )
        assert es.extract_status is canonical

    def test_paths_aliases_to_config_paths(self) -> None:
        import osm_polygon_selection.paths as p
        from osm_polygon_selection.config.paths import dataset_root as canonical
        assert p.dataset_root is canonical

    def test_runtime_config_aliases_to_config_runtime(self) -> None:
        import osm_polygon_selection.runtime_config as rc
        from osm_polygon_selection.config.runtime import (
            RuntimeConfig as canonical,
        )
        assert rc.RuntimeConfig is canonical

    def test_schema_defs_aliases_to_schema(self) -> None:
        import osm_polygon_selection.schema_defs as sd
        from osm_polygon_selection.schema import build_schema as canonical
        assert sd.build_schema is canonical

    def test_streaming_writer_aliases_to_parquet_write_runner(self) -> None:
        import osm_polygon_selection.streaming_writer as sw
        from osm_polygon_selection.parquet_write.runner import (
            write_jsonl_to_parquet as canonical,
        )
        assert sw.write_jsonl_to_parquet is canonical

    def test_streaming_writer_keeps_private_alias(self) -> None:
        """The streaming_writer facade must keep
        ``_write_jsonl_to_parquet_python_json`` for backwards-compat."""
        import osm_polygon_selection.streaming_writer as sw
        from osm_polygon_selection.parquet_write.runner import (
            _write_jsonl_to_parquet_python_json as canonical,
        )
        assert sw._write_jsonl_to_parquet_python_json is canonical

    def test_whitelist_io_aliases_to_io_whitelist(self) -> None:
        import osm_polygon_selection.whitelist_io as w
        from osm_polygon_selection.io.whitelist import (
            load_whitelist as canonical,
        )
        assert w.load_whitelist is canonical

    def test_readme_render_aliases_to_readme(self) -> None:
        import osm_polygon_selection.readme_render as rr
        from osm_polygon_selection.readme import (
            build_root_readme as canonical,
        )
        assert rr.build_root_readme is canonical
        # Legacy private alias.
        from osm_polygon_selection.readme.notes import (
            country_note as canonical_country_note,
        )
        assert rr._country_note is canonical_country_note

    def test_sample_table_aliases_to_sample_tables(self) -> None:
        import osm_polygon_selection.sample_table as st
        from osm_polygon_selection.sample_tables import (
            build_example_row_table as canonical,
        )
        assert st.build_example_row_table is canonical

    def test_pyarrow_compat_aliases_to_io_pyarrow_compat(self) -> None:
        import osm_polygon_selection.pyarrow_compat as p
        from osm_polygon_selection.io.pyarrow_compat import (
            value_counts as canonical,
        )
        assert p.value_counts is canonical

    def test_git_meta_aliases_to_config_git(self) -> None:
        import osm_polygon_selection.git_meta as g
        from osm_polygon_selection.config.git import git_sha as canonical
        assert g.git_sha is canonical

    def test_regional_pbf_meta_aliases_to_pbf_meta_regional(self) -> None:
        import osm_polygon_selection.regional_pbf_meta as r
        from osm_polygon_selection.pbf_meta.regional import (
            REGIONAL_SUB_PBFS_CANONICAL as canonical,
        )
        assert r.REGIONAL_SUB_PBFS_CANONICAL is canonical

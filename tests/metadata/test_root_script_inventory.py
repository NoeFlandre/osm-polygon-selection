"""Inventory + structural rules for root-level scripts.

Public scripts (``scripts/<name>.py``) must be thin wrappers
around a package ``runner.run_*`` or ``cli.<name>.main`` call.

A "thin" script has:

- argparse-based CLI parsing (or a tiny main that delegates to
  the package), and
- no business logic, no filesystem IO beyond arg parsing,
  no subprocess orchestration, no inline downloads, etc.

Maintainer scripts under ``scripts/operations/`` are explicitly
allowlisted; they may orchestrate subprocesses because that is
their purpose.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


SCRIPTS_ROOT = Path(__file__).resolve().parents[2] / "scripts"

# Public scripts: each must be a thin wrapper. LOC cap = 100.
PUBLIC_SCRIPTS = [
    "stage0_extract.py",
    "stage1_build_whitelist.py",
    "stage2_filter.py",
    "stage3_classify.py",
    "build_dataset.py",
    "organize_dataset.py",
    "make_split.py",
    "sample_for_map.py",
    "split_parquets.py",
    "visualize.py",
    "upload_to_hf.py",
]

# Public scripts that may exceed the strict wrapper threshold
# because they re-export legacy compat shims that downstream
# tests import. Still must NOT contain business logic.
PUBLIC_SCRIPT_OVERRIDES: dict[str, int] = {
    # The root build_dataset.py re-executes the canonical source
    # in its own namespace so test mutations of bd.HDD take
    # effect at call time.
    "build_dataset.py": 30,
}

# Operations scripts: allowlisted for HDD-side subprocess work.
OPERATIONS_DIR = "operations"

# Maximum LOC for a public script (unless overridden).
DEFAULT_MAX_PUBLIC_LOC = 50


def _loc(path: Path) -> int:
    n = 0
    for line in path.read_text().splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            n += 1
    return n


def _has_main_call_to(source: str, target_substr: str) -> bool:
    """True if the source contains a call or import of ``target_substr``."""
    return target_substr in source


class TestPublicScriptsAreThin:
    @pytest.mark.parametrize("name", PUBLIC_SCRIPTS)
    def test_public_script_under_loc_cap(self, name: str) -> None:
        path = SCRIPTS_ROOT / name
        assert path.is_file(), f"missing public script: {name}"
        cap = PUBLIC_SCRIPT_OVERRIDES.get(name, DEFAULT_MAX_PUBLIC_LOC)
        loc = _loc(path)
        assert loc <= cap, (
            f"{name} is {loc} LOC (cap {cap}). "
            f"Move logic into a cli/<name>.py package module."
        )

    @pytest.mark.parametrize("name", PUBLIC_SCRIPTS)
    def test_public_script_delegates_to_canonical(self, name: str) -> None:
        """Each public root script must delegate to a canonical
        subfolder script (or to the package).

        Two acceptable patterns:

        - ``from osm_polygon_selection... import ...`` (or
          ``from scripts.<subpkg>.<name> import ...``): direct
          package import.
        - ``runpy.run_path(`` ``<subfolder>/<name>.py`` ``)``:
          script-launcher pattern that defers to the canonical
          subfolder script.
        """
        path = SCRIPTS_ROOT / name
        text = path.read_text()
        is_direct = (
            "from osm_polygon_selection" in text
            or "from scripts." in text
        )
        is_runpy = "runpy.run_path" in text
        assert is_direct or is_runpy, (
            f"{name} does not delegate to a canonical subfolder "
            f"or to the package. Use either a package import or "
            f"a runpy.run_path launcher to the canonical subfolder script."
        )


class TestOperationsScriptsExist:
    def test_operations_dir_exists(self) -> None:
        assert (SCRIPTS_ROOT / OPERATIONS_DIR).is_dir()

    def test_batch_operations_scripts_use_package(self) -> None:
        """Multi-country batch operator scripts delegate to the operations package.

        One-off maintainer scripts (e.g. ``render_map_screenshot.py``)
        are not subject to this rule; they are documented as
        one-shot tools in the operations/README.
        """
        ops = SCRIPTS_ROOT / OPERATIONS_DIR
        # These two scripts orchestrate multi-country work and must
        # delegate to the package. Other operator scripts (e.g. the
        # Playwright screenshot capture) may be standalone.
        BATCH_OPERATOR_SCRIPTS = {
            "run_europe.py",
            "process_country_regions.py",
        }
        for name in BATCH_OPERATOR_SCRIPTS:
            p = ops / name
            assert p.is_file(), f"missing operator script: {name}"
            text = p.read_text()
            assert "from osm_polygon_selection.operations" in text, (
                f"{name} should import from osm_polygon_selection.operations"
            )


class TestNoProductionImportsFromRootFacades:
    """Production code under ``src/osm_polygon_selection/`` (and
    its subpackages) must NOT import from a root-level facade.
    Internal code uses canonical subpackage paths.

    Note: root facade .py files no longer exist; the alias
    mechanism in :mod:`osm_polygon_selection.compat.import_aliases`
    redirects legacy paths to canonical subpackages. This test
    additionally enforces that no production code uses the
    legacy paths either, even though they would still resolve.
    """

    SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "osm_polygon_selection"

    FORBIDDEN_LEGACY_PATHS = [
        "from osm_polygon_selection.streaming_writer import",
        "from osm_polygon_selection.sample_table import",
        "from osm_polygon_selection.readme_render import",
        "from osm_polygon_selection.regional_pbf_meta import",
        "from osm_polygon_selection.schema_defs import",
        "from osm_polygon_selection.country_table import",
        "from osm_polygon_selection.runtime_config import",
        "from osm_polygon_selection.paths import",
        "from osm_polygon_selection.git_meta import",
        "from osm_polygon_selection.whitelist_io import",
        "from osm_polygon_selection.pyarrow_compat import",
        "from osm_polygon_selection.extract_status import",
    ]

    def test_no_legacy_path_imports_in_production(self) -> None:
        offenders: list[tuple[Path, str]] = []
        for py in self.SRC_ROOT.rglob("*.py"):
            text = py.read_text()
            for forbidden in self.FORBIDDEN_LEGACY_PATHS:
                if forbidden in text:
                    offenders.append((py, forbidden))
        assert not offenders, (
            "Production code uses a legacy root import path (forbidden). "
            "Use the canonical subpackage path:\n"
            + "\n".join(f"  {p.relative_to(self.SRC_ROOT)}: {f}" for p, f in offenders)
        )

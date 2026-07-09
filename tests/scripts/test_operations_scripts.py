"""Smoke tests for the maintainer-only scripts under scripts/operations/.

The scripts themselves run subprocesses and require playwright/curl;
these tests only pin:
- argparse / arg-parsing behavior
- env-var override paths
- the absence of operator-specific hard-coded local paths in source

No real PBF downloads or browser launches happen here.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
OPS_DIR = SCRIPTS_DIR / "operations"


def _load(script_name: str):
    spec = importlib.util.spec_from_file_location(
        f"_operations_{script_name}", OPS_DIR / script_name,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load {script_name}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_render_map_screenshot_respects_env_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """OSM_MAP_PREVIEW_PNG overrides the default output path."""
    out_png = tmp_path / "custom_preview.png"
    monkeypatch.setenv("OSM_MAP_PREVIEW_PNG", str(out_png))
    monkeypatch.setenv("OSM_REPO_ROOT", str(tmp_path))
    # The logic lives in osm_polygon_selection.operations.screenshot;
    # the script is a thin launcher.
    from osm_polygon_selection.operations.screenshot import resolve_output_path
    assert resolve_output_path() == out_png


def test_render_map_screenshot_default_uses_repo_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Without OSM_MAP_PREVIEW_PNG, default is <OSM_REPO_ROOT>/data/dataset/map_preview.png."""
    monkeypatch.delenv("OSM_MAP_PREVIEW_PNG", raising=False)
    monkeypatch.setenv("OSM_REPO_ROOT", str(tmp_path))
    from osm_polygon_selection.operations.screenshot import resolve_output_path
    assert resolve_output_path() == tmp_path / "data" / "dataset" / "map_preview.png"


def test_process_country_regions_has_no_hardcoded_user_path() -> None:
    """process_country_regions.py must not contain operator paths in source."""
    text = (OPS_DIR / "process_country_regions.py").read_text()
    assert "/Users/noeflandre" not in text, (
        "process_country_regions.py contains a hard-coded /Users/noeflandre/... path"
    )


def test_run_europe_has_no_hardcoded_user_path() -> None:
    """run_europe.py must not contain operator paths in source."""
    text = (OPS_DIR / "run_europe.py").read_text()
    assert "/Users/noeflandre" not in text


def test_operations_scripts_directory_exists() -> None:
    """scripts/operations/ exists and contains the expected files."""
    assert OPS_DIR.is_dir()
    expected = {
        "complete_pipeline.sh",
        "process_country_regions.py",
        "render_map_screenshot.py",
        "run_country.sh",
        "run_europe.py",
    }
    actual = {p.name for p in OPS_DIR.iterdir()}
    assert expected.issubset(actual), f"missing: {expected - actual}"


# Wording pin: no agent-era language should leak into operations
# scripts. These scripts run on the operator's machine; "agent" is
# not a meaningful term for maintainer documentation.
FORBIDDEN_OPERATIONS_WORDS = [
    "agent runtime",
    "agent call",
    "agent session",
    "Codex",
]


@pytest.mark.parametrize("script", [
    "complete_pipeline.sh",
    "process_country_regions.py",
    "render_map_screenshot.py",
    "run_country.sh",
    "run_europe.py",
])
@pytest.mark.parametrize("forbidden", FORBIDDEN_OPERATIONS_WORDS)
def test_operations_scripts_have_no_agent_era_wording(
    script: str, forbidden: str,
) -> None:
    """Operations scripts must not contain agent-era wording."""
    text = (OPS_DIR / script).read_text()
    assert forbidden not in text, (
        f"{script} contains agent-era wording {forbidden!r}; "
        f"operator scripts should use 'operator' / 'interactive session' / "
        f"'long-running local process' instead."
    )


# Env-var path pin: hard-coded local paths should not leak into
# operations scripts. The "${VAR:-/path/...}" env-fallback syntax
# is allowed because it's the documented operator default; any
# other absolute /Users/ or /Volumes/ mention is a regression.
def _strip_env_fallbacks(text: str) -> str:
    """Remove ``${VAR:-/absolute/path}`` and ``${VAR:-default}``
    occurrences so we can grep for un-overridable absolute paths."""
    import re
    return re.sub(r"\$\{[^}]+:-\s*[^}]*\}", "<env-fallback>", text)


FORBIDDEN_PATH_PATTERNS = [
    "/Users/",
    "/Volumes/",
]


@pytest.mark.parametrize("script", [
    "complete_pipeline.sh",
    "process_country_regions.py",
    "render_map_screenshot.py",
    "run_country.sh",
    "run_europe.py",
])
@pytest.mark.parametrize("forbidden", FORBIDDEN_PATH_PATTERNS)
def test_operations_scripts_have_no_machine_specific_paths(
    script: str, forbidden: str,
) -> None:
    """Operations scripts must not contain machine-specific absolute paths.

    Exception: ``${VAR:-/path}`` env-fallback syntax (the operator
    default). Those are intentional and env-overridable.
    """
    text = _strip_env_fallbacks((OPS_DIR / script).read_text())
    assert forbidden not in text, (
        f"{script} contains machine-specific path {forbidden!r}; "
        f"operations scripts must use $OSM_DATA_ROOT / $OSM_REPO_ROOT env vars."
    )

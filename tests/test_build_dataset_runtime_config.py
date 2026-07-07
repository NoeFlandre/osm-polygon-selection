"""Pin that scripts/build_dataset.py honors $OSM_DATA_ROOT for HDD/PROC paths.

This test never touches the real external HDD. It uses isolated
tmp_path fixtures and runs the script's module-level initialization
in a subprocess so the RuntimeConfig.from_env() evaluation happens
freshly with a controlled environment.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path


def _run_probe(env_root: str) -> dict[str, str]:
    """Run a tiny script that imports the build_dataset module and prints HDD/PROC.

    This exercises the module-level RuntimeConfig.from_env() call
    inside scripts/build_dataset.py.
    """
    code = textwrap.dedent(
        f"""
        import os, sys
        sys.path.insert(0, "scripts")
        os.environ["OSM_DATA_ROOT"] = {env_root!r}
        # Pre-import the runtime_config and dataset_build.records to verify
        # they were not cached on the real HDD path.
        import build_dataset
        # Don't actually run main() (it would scan the real filesystem).
        print("HDD=" + str(build_dataset.HDD))
        print("PROC=" + str(build_dataset.PROC))
        print("WL_MODULE_DEFAULT=" + str(build_dataset._load_whitelist_module_path()))
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    out: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def test_build_dataset_uses_osm_data_root(tmp_path: Path) -> None:
    """When $OSM_DATA_ROOT is set, build_dataset.HDD and PROC reflect it."""
    fake_root = str(tmp_path / "fake-data-root")
    out = _run_probe(fake_root)
    assert out["HDD"] == fake_root
    assert out["PROC"] == str(Path(fake_root) / "processed")


def test_build_dataset_default_hdd_when_no_env(monkeypatch, tmp_path: Path) -> None:
    """When $OSM_DATA_ROOT is unset, build_dataset falls back to the legacy default.

    We don't assert the exact default (it is the user's external HDD); we
    just assert the module imports successfully and the HDD path
    contains 'osm-polygon-selection' (i.e. it was resolved via
    default_data_root()).
    """
    monkeypatch.delenv("OSM_DATA_ROOT", raising=False)
    code = textwrap.dedent(
        """
        import sys
        sys.path.insert(0, "scripts")
        import build_dataset
        print("HDD=" + str(build_dataset.HDD))
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    hdd = next(
        (line.split("=", 1)[1] for line in result.stdout.splitlines() if line.startswith("HDD=")),
        "",
    )
    assert "osm-polygon-selection" in hdd

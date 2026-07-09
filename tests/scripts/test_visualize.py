"""CLI smoke test for ``scripts/visualize.py``.

Domain behavior is covered by ``tests/visualization/test_visualization_package.py``.
This file only pins CLI delegation + default --limit value.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
VISUALIZE = SCRIPTS_DIR / "visualize.py"


def _make_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def _row(country: str, lon: float, lat: float) -> dict:
    return {
        "country": country,
        "osm_id": 1,
        "centroid_lon": lon,
        "centroid_lat": lat,
        "area_km2": 0.5,
        "size_bin": "small",
        "matched_tag": "natural=water",
        "tags": ["natural=water"],
    }


def test_cli_renders_countries(tmp_path: Path) -> None:
    jsonl = tmp_path / "sample.jsonl"
    out_html = tmp_path / "map.html"
    countries = [f"country_{i:02d}" for i in range(10)]
    rows = [_row(c, float(i), float(i)) for i, c in enumerate(countries)]
    _make_jsonl(jsonl, rows)

    result = subprocess.run(
        [sys.executable, str(VISUALIZE), str(jsonl), str(out_html)],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    html = out_html.read_text()
    for c in countries:
        assert c in html, f"{c} missing from rendered map (truncated)"


def test_cli_help_runs() -> None:
    """``--help`` must not require any network or files."""
    result = subprocess.run(
        [sys.executable, str(VISUALIZE), "--help"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    assert "JSONL" in result.stdout or "--limit" in result.stdout


def test_cli_default_limit_at_least_5000() -> None:
    """The hard-coded default --limit must be large enough."""
    from osm_polygon_selection.visualization import MAX_DEFAULT_LIMIT
    assert MAX_DEFAULT_LIMIT >= 5000

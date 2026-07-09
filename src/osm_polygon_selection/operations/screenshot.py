"""Headless-browser screenshot of the folium sample map.

Used by ``scripts/operations/render_map_screenshot.py`` to
capture a PNG of ``/tmp/sample_map.html`` for the dataset
README on the HuggingFace page.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

# Default output: <repo_root>/data/dataset/map_preview.png. The
# repo root is $OSM_REPO_ROOT if set, else the script's cwd's
# resolved path.
DEFAULT_REPO_ROOT = Path(os.environ.get("OSM_REPO_ROOT", Path.cwd().resolve()))


# Wider than tall: folium defaults to a square map; 1600x1100 lets
# us see Europe without much empty space at top/bottom.
WIDTH = 1600
HEIGHT = 1100
# Wait this long for the tile layer + all markers to load before
# taking the screenshot. folium tiles come from openstreetmap.org
# and can take a few seconds.
LOAD_WAIT_S = 8

SAMPLE_HTML = Path("/tmp/sample_map.html")


def resolve_output_path() -> Path:
    """Return the PNG output path (honors ``$OSM_MAP_PREVIEW_PNG``)."""
    env_png = os.environ.get("OSM_MAP_PREVIEW_PNG")
    if env_png:
        return Path(env_png)
    # Re-resolve on every call so monkeypatched env vars take effect.
    repo_root = Path(os.environ.get("OSM_REPO_ROOT", Path.cwd().resolve()))
    return repo_root / "data" / "dataset" / "map_preview.png"


def render_screenshot(
    *,
    sample_html: Path | None = None,
    out_png: Path | None = None,
    width: int = WIDTH,
    height: int = HEIGHT,
    load_wait_s: int = LOAD_WAIT_S,
) -> Path:
    """Launch a headless Chromium, navigate to ``sample_html``,
    wait for tiles to load, and save a PNG to ``out_png``.

    Returns the resolved output path. Raises :class:`FileNotFoundError`
    if ``sample_html`` is missing.
    """
    from playwright.sync_api import sync_playwright

    # Read SAMPLE_HTML at call time so monkeypatching the module
    # attribute takes effect in tests.
    if sample_html is None:
        sample_html = SAMPLE_HTML
    if not sample_html.exists():
        raise FileNotFoundError(
            f"{sample_html} not found; run scripts/sample_for_map.py first"
        )
    out_png = out_png or resolve_output_path()
    out_png.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": width, "height": height})
        page = context.new_page()
        page.goto(sample_html.as_uri())
        page.wait_for_load_state("networkidle", timeout=30_000)
        time.sleep(load_wait_s)
        page.screenshot(path=str(out_png), full_page=False)
        browser.close()
    return out_png


def main() -> int:
    try:
        out_png = render_screenshot()
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return 1
    size_mb = out_png.stat().st_size / 1_048_576
    print(f"saved {out_png} ({size_mb:.1f} MB)")
    return 0


__all__ = [
    "DEFAULT_REPO_ROOT",
    "HEIGHT",
    "LOAD_WAIT_S",
    "SAMPLE_HTML",
    "WIDTH",
    "main",
    "render_screenshot",
    "resolve_output_path",
]

"""Render the sample map and capture a screenshot for the dataset README.

Renders /tmp/sample_map.html in a headless Chromium browser, waits for
the folium tiles to load, and saves a high-resolution PNG to
data/dataset/map_preview.png.

The PNG is then embedded in data/dataset/README.md via a markdown
image tag so people landing on the HuggingFace dataset page can see
the geographic distribution at a glance.
"""

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

SAMPLE_HTML = Path("/tmp/sample_map.html")
OUT_PNG = Path("/Users/noeflandre/osm-polygon-selection/data/dataset/map_preview.png")

# Wider than tall: folium defaults to a square map; 1600x1100 lets us
# see Europe without much empty space at top/bottom.
WIDTH = 1600
HEIGHT = 1100
# Wait this long for the tile layer + all markers to load before
# taking the screenshot. folium tiles come from openstreetmap.org
# and can take a few seconds.
LOAD_WAIT_S = 8


def main() -> None:
    if not SAMPLE_HTML.exists():
        print(f"ERROR: {SAMPLE_HTML} not found; run scripts/sample_for_map.py first")
        sys.exit(1)

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": WIDTH, "height": HEIGHT})
        page = context.new_page()
        page.goto(SAMPLE_HTML.as_uri())
        # Give folium tiles + leaflet JS time to fetch and render.
        page.wait_for_load_state("networkidle", timeout=30_000)
        time.sleep(LOAD_WAIT_S)
        page.screenshot(path=str(OUT_PNG), full_page=False)
        browser.close()

    size_mb = OUT_PNG.stat().st_size / 1_048_576
    print(f"saved {OUT_PNG} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
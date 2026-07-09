"""Render the sample map and capture a screenshot for the dataset README.

Thin wrapper around :mod:`osm_polygon_selection.operations.screenshot`.
"""

from osm_polygon_selection.operations.screenshot import (
    main as _screenshot_main,
)

__all__ = ["_screenshot_main"]

if __name__ == "__main__":
    raise SystemExit(_screenshot_main())

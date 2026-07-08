"""Folder README rendering.

Produces short READMEs for each of the four subfolders
(``per_country/``, ``combined/``, ``sample/``, ``preview/``).
The template dict lives in ``readme.templates.FOLDER_TEMPLATES``.
"""

from __future__ import annotations

from osm_polygon_selection.readme.templates import FOLDER_TEMPLATES


def build_folder_readme(folder: str, n_countries: int) -> str:
    """Render a short README for one of the four subfolders."""
    if folder not in FOLDER_TEMPLATES:
        raise ValueError(
            f"unknown folder: {folder!r}; expected one of {list(FOLDER_TEMPLATES)}"
        )
    return FOLDER_TEMPLATES[folder].format(n_countries=n_countries)

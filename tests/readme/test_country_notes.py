"""Pin that `build_country_readme` uses the package's country notes.

Regression: readme_render.py used to keep its own COUNTRY_NOTES
dict and its own _country_note function, leaving two sources of
truth alongside osm_polygon_selection.country_notes. The unified
build_country_readme now sources notes from the package.
"""

from __future__ import annotations

import inspect

import pytest


def test_build_country_readme_uses_package_country_note() -> None:
    """build_country_readme's note must come from osm_polygon_selection.country_notes."""
    from osm_polygon_selection.country_notes import country_note, COUNTRY_NOTES
    from osm_polygon_selection.readme_render import build_country_readme

    # Take a country that's known to have a curated note in the
    # package. We pick georgia (the package has a multi-line note).
    country = "georgia"
    pkg_note = country_note(country, n_polygons=1000, extract_status="clean")
    assert country in COUNTRY_NOTES

    rendered = build_country_readme(
        country=country,
        n_polygons=1000,
        extract_status="clean",
        pbf_date="2026-01-01",
    )

    # The rendered README must include the package's curated note.
    assert pkg_note in rendered, (
        f"build_country_readme did not surface the package's note for {country}.\n"
        f"package note: {pkg_note!r}\nrendered:\n{rendered[:500]}"
    )


def test_readme_render_does_not_define_its_own_country_note() -> None:
    """The module-level readme_render.COUNTRY_NOTES should now be a view over
    the package's notes (or include them), not a parallel dict with the
    same key but a different value."""
    from osm_polygon_selection import country_notes as pkg
    from osm_polygon_selection import readme_render

    # For each note in the package, the readme_render view should have
    # the SAME note value (not a divergent one).
    for k, v in pkg.COUNTRY_NOTES.items():
        if k in readme_render.COUNTRY_NOTES:
            assert readme_render.COUNTRY_NOTES[k] == v, (
                f"readme_render.COUNTRY_NOTES[{k!r}] disagrees with the package: "
                f"render={readme_render.COUNTRY_NOTES[k]!r} vs package={v!r}"
            )


def test_no_local_country_note_function_in_readme_render() -> None:
    """The legacy _country_note function in readme_render should delegate
    to the package, not re-implement the lookup."""
    from osm_polygon_selection import readme_render

    fn = getattr(readme_render, "_country_note", None)
    assert fn is not None, "readme_render._country_note must still exist"
    # The function must reference the package's curated notes.
    src = inspect.getsource(fn)
    assert "country_notes" in src or "_PKG_COUNTRY_NOTES" in src, (
        "readme_render._country_note should consult the package's country notes"
    )

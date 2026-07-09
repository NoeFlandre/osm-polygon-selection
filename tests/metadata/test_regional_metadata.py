"""Pin that the regional sub-PBF map is a single source of truth.

These tests verify that:

1. ``regional_pbf_meta.REGIONAL_SUB_PBFS_CANONICAL`` is the only
   inline dict defining the regional map.
2. ``dataset_build.countries.REGIONAL_CHILDREN`` and
   ``country_notes.REGIONAL_SUB_PBFS`` are both derived from it.
3. The build side keeps the superset (haute-normandie, bermuda,
   falklands) even when the README side is filtered to a subset.
4. A runtime sentinel test fails if anyone re-introduces a parallel
   inline dict literal.
"""

from __future__ import annotations


def test_canonical_module_is_the_only_source() -> None:
    """The canonical map is defined in pbf_meta.regional and exposed
    to consumers as REGIONAL_SUB_PBFS_CANONICAL."""
    from osm_polygon_selection.pbf_meta.regional import (
        ALL_REGIONAL_CANONICAL,
        REGIONAL_SUB_PBFS_CANONICAL,
    )

    # It must be a non-empty dict[str, set[str]].
    assert isinstance(REGIONAL_SUB_PBFS_CANONICAL, dict)
    assert len(REGIONAL_SUB_PBFS_CANONICAL) > 0
    for parent, children in REGIONAL_SUB_PBFS_CANONICAL.items():
        assert isinstance(children, set)
        assert all(isinstance(c, str) for c in children)

    # ALL_REGIONAL_CANONICAL must be the flat union.
    expected = {c for cs in REGIONAL_SUB_PBFS_CANONICAL.values() for c in cs}
    assert ALL_REGIONAL_CANONICAL == expected


def test_countries_derives_from_canonical() -> None:
    """dataset_build.countries.REGIONAL_CHILDREN == REGIONAL_SUB_PBFS_CANONICAL."""
    from osm_polygon_selection.dataset_build.countries import (
        ALL_REGIONAL,
        REGIONAL_CHILDREN,
    )
    from osm_polygon_selection.pbf_meta.regional import (
        ALL_REGIONAL_CANONICAL,
        REGIONAL_SUB_PBFS_CANONICAL,
    )

    assert REGIONAL_CHILDREN == REGIONAL_SUB_PBFS_CANONICAL
    assert ALL_REGIONAL == ALL_REGIONAL_CANONICAL


def test_country_notes_derives_from_canonical() -> None:
    """country_notes.REGIONAL_SUB_PBFS has the same keys; lists are sorted copies
    of the canonical sets."""
    from osm_polygon_selection.country_notes import REGIONAL_SUB_PBFS
    from osm_polygon_selection.regional_pbf_meta import REGIONAL_SUB_PBFS_CANONICAL

    assert set(REGIONAL_SUB_PBFS.keys()) == set(REGIONAL_SUB_PBFS_CANONICAL.keys())
    for parent, children_list in REGIONAL_SUB_PBFS.items():
        assert set(children_list) == REGIONAL_SUB_PBFS_CANONICAL[parent], (
            f"country_notes.REGIONAL_SUB_PBFS[{parent!r}] disagrees with the canonical map"
        )
        # And the lists are sorted (deterministic order).
        assert children_list == sorted(children_list)


def test_build_side_has_superset_including_haute_normandie_bermuda_falklands() -> None:
    """Pin the build side's superset behavior. The build pipeline
    must filter out every regional sub-PBF, including ones that
    aren't surfaced in the public README."""
    from osm_polygon_selection.dataset_build.countries import ALL_REGIONAL

    assert "haute-normandie" in ALL_REGIONAL
    assert "bermuda" in ALL_REGIONAL
    assert "falklands" in ALL_REGIONAL


def test_no_parallel_inline_dict_in_countries_or_country_notes() -> None:
    """No regression: the inline regional map dict must not be
    re-introduced into countries.py or country_notes.py."""
    import inspect

    from osm_polygon_selection import country_notes, dataset_build
    from osm_polygon_selection.dataset_build import countries as c_mod

    for mod in (c_mod, country_notes):
        src = inspect.getsource(mod)
        # The old inline dict literal is a multi-line "{ ... }" with
        # more than 5 quoted strings and the comment "# All regional".
        assert "# All regional" not in src, (
            f"{mod.__name__} re-introduced a parallel inline regional dict"
        )
        # The data is sourced from pbf_meta.regional instead.
        assert "pbf_meta" in src

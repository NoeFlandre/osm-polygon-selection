"""osm_polygon_selection package.

Importing this package installs backwards-compat ``sys.modules``
aliases so legacy import paths (``osm_polygon_selection.<old>``)
resolve to their canonical subpackages. See
:mod:`osm_polygon_selection.compat.import_aliases` for details.

The package also exposes a PEP 562 ``__getattr__`` that resolves
legacy submodule names even when the package itself is not
imported first.
"""

from osm_polygon_selection.compat.import_aliases import (  # noqa: F401
    LEGACY_ALIASES,
    install_sys_modules_aliases,
)

# Pre-populate sys.modules so the legacy root-level names resolve
# to their canonical subpackages for the rest of the process.
install_sys_modules_aliases()


def __getattr__(name: str):
    """PEP 562: lazy submodule resolution for legacy root-level names."""
    from osm_polygon_selection.compat.import_aliases import _resolve_legacy
    if name in LEGACY_ALIASES:
        return _resolve_legacy(name)
    raise AttributeError(f"module 'osm_polygon_selection' has no attribute {name!r}")


def __dir__() -> list[str]:
    """Include legacy names in tab-completion / dir() listing."""
    return sorted(set(__all__) | set(LEGACY_ALIASES))


__all__: list[str] = []

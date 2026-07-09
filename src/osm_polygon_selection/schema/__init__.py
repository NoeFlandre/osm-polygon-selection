"""PyArrow schema definitions + geometry encoding helpers.

Canonical location for the dataset schema. Used by:

- :mod:`osm_polygon_selection.dataset_build` to write per-country parquets
- :mod:`osm_polygon_selection.readme` to render the schema table
- :mod:`osm_polygon_selection.dataset_split` to add the ``split`` column

The geometry column is conditional: ``wkt`` (default, text),
``wkb`` (binary, ~50% smaller), or ``none`` (drop entirely). The
``split`` column is optional — included only after
``make_split`` has been run.

Backwards-compat: ``osm_polygon_selection.schema_defs`` is a
thin facade re-exporting this package's public surface.
"""

from osm_polygon_selection.schema.defs import (
    COLUMN_DESCRIPTIONS,
    COLUMN_TYPES,
    GEOMETRY_ENCODING_DEFAULT,
    build_schema,
    encode_geometry,
    get_column_order,
)

__all__ = [
    "COLUMN_DESCRIPTIONS",
    "COLUMN_TYPES",
    "GEOMETRY_ENCODING_DEFAULT",
    "build_schema",
    "encode_geometry",
    "get_column_order",
]

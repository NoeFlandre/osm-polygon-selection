"""Tests for osm_polygon_selection.schema_defs.

TDD red phase: written before src/osm_polygon_selection/schema_defs.py.
"""

from __future__ import annotations

import pyarrow as pa

from osm_polygon_selection.schema_defs import (
    GEOMETRY_ENCODING_DEFAULT,
    COLUMN_DESCRIPTIONS,
    COLUMN_TYPES,
    build_schema,
    encode_geometry,
    get_column_order,
)


class TestBuildSchema:
    def test_default_encoding_is_wkt(self) -> None:
        assert GEOMETRY_ENCODING_DEFAULT == "wkt"

    def test_schema_has_all_required_columns(self) -> None:
        schema = build_schema()
        for col in (
            "osm_id", "osm_type", "centroid_lon", "centroid_lat",
            "area_km2", "tags", "matched_tag", "continent", "size_bin",
            "country", "extract_status", "pbf_date",
        ):
            assert col in schema.names

    def test_schema_includes_geometry_wkt_by_default(self) -> None:
        schema = build_schema()
        assert "geometry_wkt" in schema.names

    def test_schema_with_wkb_encoding(self) -> None:
        schema = build_schema(geometry_encoding="wkb")
        assert "geometry_wkb" in schema.names
        assert "geometry_wkt" not in schema.names

    def test_schema_with_no_geometry(self) -> None:
        schema = build_schema(geometry_encoding="none")
        assert "geometry_wkt" not in schema.names
        assert "geometry_wkb" not in schema.names

    def test_split_column_added_when_requested(self) -> None:
        schema = build_schema(include_split=True)
        assert "split" in schema.names

    def test_split_column_absent_by_default(self) -> None:
        schema = build_schema()
        assert "split" not in schema.names


class TestEncodeGeometry:
    def test_wkt_passthrough(self) -> None:
        wkt = "POLYGON ((0 0, 1 0, 1 1, 0 0))"
        assert encode_geometry(wkt, "wkt") == wkt

    def test_none_returns_none(self) -> None:
        assert encode_geometry(None, "wkt") is None

    def test_empty_returns_none(self) -> None:
        assert encode_geometry("", "wkt") is None

    def test_encoding_none_returns_none(self) -> None:
        assert encode_geometry("POLYGON ((0 0))", "none") is None

    def test_wkb_encodes_bytes(self) -> None:
        wkt = "POLYGON ((0 0, 1 0, 1 1, 0 0))"
        result = encode_geometry(wkt, "wkb")
        assert isinstance(result, bytes)
        assert len(result) > 0


class TestColumnDescriptions:
    def test_osm_id_described(self) -> None:
        assert "OSM object id" in COLUMN_DESCRIPTIONS["osm_id"]

    def test_geometry_wkt_described(self) -> None:
        assert "WKT" in COLUMN_DESCRIPTIONS["geometry_wkt"]

    def test_split_described(self) -> None:
        assert "train" in COLUMN_DESCRIPTIONS["split"]

    def test_all_descriptions_have_a_value(self) -> None:
        for k, v in COLUMN_DESCRIPTIONS.items():
            assert v, f"empty description for {k}"

    def test_column_types_has_string_for_string_cols(self) -> None:
        assert COLUMN_TYPES["matched_tag"] == "string"
        assert COLUMN_TYPES["size_bin"] == "string"


class TestGetColumnOrder:
    def test_returns_list(self) -> None:
        cols = get_column_order()
        assert isinstance(cols, list)
        assert len(cols) >= 12

    def test_includes_geometry_wkt_by_default(self) -> None:
        cols = get_column_order()
        assert "geometry_wkt" in cols

    def test_includes_split_when_requested(self) -> None:
        cols = get_column_order(include_split=True)
        assert "split" in cols
        assert cols[-1] == "split"  # appended last

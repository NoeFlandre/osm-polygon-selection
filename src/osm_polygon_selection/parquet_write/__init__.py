"""Public API for the parquet_write pipeline.

Layout:
- :mod:`.atomic` — atomic write helpers (temp + replace)
- :mod:`.jsonl` — Python-JSONL per-row legacy writer
- :mod:`.transform` — table transformation (build_columns, reshape)
- :mod:`.matched_tags` — matched_tag backfill
"""

from osm_polygon_selection.parquet_write.atomic import (
    atomic_write_empty_parquet,
    atomic_write_parquet,
)
from osm_polygon_selection.parquet_write.jsonl import (
    write_jsonl_to_parquet_python_json,
)
from osm_polygon_selection.parquet_write.matched_tags import (
    maybe_backfill_matched_tag,
    maybe_backfill_matched_tag_pa,
)
from osm_polygon_selection.parquet_write.transform import (
    build_columns,
    reshape_parsed_table,
    split_centroid,
)

__all__ = [
    "atomic_write_empty_parquet",
    "atomic_write_parquet",
    "build_columns",
    "maybe_backfill_matched_tag",
    "maybe_backfill_matched_tag_pa",
    "reshape_parsed_table",
    "split_centroid",
    "write_jsonl_to_parquet_python_json",
]

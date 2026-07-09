"""Matched-tag backfill for the parquet_write pipeline.

Two flavors:
- Python-list backfill (legacy per-row path)
- pyarrow Table backfill (the fast pyarrow.json path)
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import pyarrow as pa


def maybe_backfill_matched_tag(
    cols: dict[str, list],
    whitelist_path: Path | None,
) -> None:
    """If any row has empty matched_tag, fill it from the whitelist.

    Modifies ``cols["matched_tag"]`` in place.
    """
    if whitelist_path is None:
        return
    matched = cols["matched_tag"]
    needs_fill = [i for i, m in enumerate(matched) if not m]
    if not needs_fill:
        return
    from osm_polygon_selection.io.whitelist import (
        clear_whitelist_cache,
        load_whitelist,
        vectorized_compute_matched_tags,
    )
    clear_whitelist_cache()
    load_whitelist(whitelist_path)
    tags_to_fill = pa.array([cols["tags"][i] for i in needs_fill])
    out = vectorized_compute_matched_tags(tags_to_fill, whitelist_path)
    filled = out.to_pylist()
    for idx, fill_idx in enumerate(needs_fill):
        cols["matched_tag"][fill_idx] = filled[idx]


def maybe_backfill_matched_tag_pa(
    table: pa.Table,
    whitelist_path: Path,
) -> pa.Table:
    """Vectorized matched_tag backfill on a pyarrow Table."""
    matched = table.column("matched_tag").to_pylist()
    needs_fill_idx = [i for i, m in enumerate(matched) if not m]
    if not needs_fill_idx:
        return table
    from osm_polygon_selection.io.whitelist import (
        clear_whitelist_cache,
        load_whitelist,
        vectorized_compute_matched_tags,
    )
    clear_whitelist_cache()
    load_whitelist(whitelist_path)
    tags = table.column("tags")
    tags_to_fill = tags.take(needs_fill_idx)
    out = vectorized_compute_matched_tags(tags_to_fill, whitelist_path)
    filled = list(out.to_pylist())
    matched_arr = list(matched)
    for idx, fill_value in zip(needs_fill_idx, filled):
        matched_arr[idx] = fill_value
    new_matched_col = pa.array(
        matched_arr, type=table.schema.field("matched_tag").type
    )
    return table.set_column(
        table.schema.get_field_index("matched_tag"), "matched_tag", new_matched_col
    )

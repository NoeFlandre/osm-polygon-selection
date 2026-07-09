"""Typed wrappers around ``pyarrow.compute`` functions where stubs lag runtime.

The pyarrow type stubs do not yet include some functions that are
present at runtime (e.g. ``equal``, ``is_in``, ``value_counts``,
``list_element``). This module bridges that gap by re-exporting the
runtime functions with explicit type annotations.

The ``# type: ignore[attr-defined]`` comments are intentional —
they suppress the stub-gap warning since the function exists at
runtime. Mypy errors that point to ``pyarrow.compute`` not having
the attribute are the symptom; this file is the cure.
"""

from __future__ import annotations

from typing import Any

import pyarrow as pa
import pyarrow.compute as pc

__all__ = ["equal", "is_in", "list_element", "value_counts"]


def equal(left: pa.Array | pa.ChunkedArray, right: Any) -> pa.Array:
    """Typed wrapper for ``pyarrow.compute.equal``."""
    return pc.equal(left, right)  # type: ignore[attr-defined]


def is_in(values: pa.Array, value_set: pa.Array) -> pa.Array:
    """Typed wrapper for ``pyarrow.compute.is_in``."""
    return pc.is_in(values, value_set=value_set)  # type: ignore[attr-defined]


def value_counts(array: pa.Array) -> pa.Table:
    """Typed wrapper for ``pyarrow.compute.value_counts``."""
    return pc.value_counts(array)  # type: ignore[attr-defined]


def list_element(
    array: pa.Array | pa.ChunkedArray, index: int
) -> pa.Array | pa.ChunkedArray:
    """Typed wrapper for ``pyarrow.compute.list_element``."""
    return pc.list_element(array, index)  # type: ignore[attr-defined]

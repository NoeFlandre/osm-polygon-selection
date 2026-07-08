"""Markdown rendering helpers for sample tables.

Pure formatters. No IO.
"""

from __future__ import annotations


def truncate(s: str | None, max_len: int = 100) -> str:
    """Truncate ``s`` to ``max_len`` chars with a trailing ``...`` if cut."""
    if s is None:
        return ""
    s = str(s)
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def build_size_bin_distribution_table(
    dist: list[tuple[str, int, float]],
) -> str:
    """Render the size-bin distribution as a markdown table."""
    out = "| size_bin | count | pct |\n|----------|-------|-----|\n"
    for sb, n, pct in dist:
        out += f"| {sb} | {n:,} | {pct:.1f}% |\n"
    total = sum(c for _, c, _ in dist)
    out += f"| **Total** | {total:,} | 100.0% |\n"
    return out


__all__ = ["build_size_bin_distribution_table", "truncate"]

"""Extract status detection per country.

A country is "clean" if its Stage 0 extract process finished
(wrote a `.run.json` log file) before being interrupted. For
countries processed via regional sub-PBFs, each sub-region has its
own `01_extracted_<region>.jsonl.run.json`; the country is clean
if ANY of those exist.

A country is "killed" otherwise (missing dir, no run.json).
"""

from __future__ import annotations

from pathlib import Path


def extract_status(country_dir: Path) -> str:
    """Return "clean" or "killed" for the given country directory.

    Args:
        country_dir: path to the per-country directory
            (e.g. `processed/france/`). Existence is not required
            (returns "killed" if missing).

    Returns:
        "clean" if any run.json exists in the country dir,
        else "killed".
    """
    if not country_dir.is_dir():
        return "killed"
    # Merged run.json
    if (country_dir / "01_extracted.jsonl.run.json").is_file():
        return "clean"
    # Any sub-region run.json
    for _ in country_dir.glob("01_extracted_*.jsonl.run.json"):
        return "clean"
    return "killed"


def is_country_clean(country_dir: Path) -> bool:
    """Boolean shorthand for `extract_status(...) == "clean"`."""
    return extract_status(country_dir) == "clean"

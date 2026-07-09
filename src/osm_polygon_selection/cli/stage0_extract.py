"""Stage 0 CLI: PBF -> JSONL of polygons.

Resumable + stoppable:

- ``--limit N`` cap the number of NEW polygons in this run.
- ``--max-seconds N`` cap the wall-clock time of this run.

Either cap, when hit, produces a clean exit. The WAL is preserved,
so re-running with no cap (or a higher one) picks up where you left
off. The wall-clock cap is essential for huge PBFs (france 4.7GB)
where the first-pass osmium index build can take 30+ minutes and
produces no polygons until it finishes.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from osm_polygon_selection.stages.extract import extract


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pbf", type=Path, help="Path to .osm.pbf file")
    parser.add_argument("out", type=Path, help="Path to output .jsonl file")
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Stop after this many NEW polygons in this run",
    )
    parser.add_argument(
        "--max-seconds", type=float, default=None,
        help="Stop after this many wall-clock seconds. Useful for huge "
             "PBFs whose first-pass index build can take 30+ minutes; "
             "re-run with no limit (or higher) to resume. The WAL "
             "preserves all already-seen ids across runs.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    n = extract(args.pbf, args.out, limit=args.limit, max_seconds=args.max_seconds)
    print(f"Wrote {n} polygons to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

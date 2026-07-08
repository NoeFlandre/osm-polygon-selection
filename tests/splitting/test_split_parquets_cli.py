"""Tests for `scripts/split_parquets.py` CLI argument handling.

The CLI must derive `--source` and `--out` from `--root` when the
former are not explicitly supplied. Regression: previously the
defaults were computed at import time, so passing `--root X` did
not pick up `X/combined/all_world.parquet` and `X/splits`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


def _write_source_with_splits(path: Path) -> None:
    table = pa.table(
        {
            "country": ["a", "b", "c", "d", "e"],
            "split": ["train", "val", "test", "train", "val"],
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path)


def test_cli_root_derives_source_and_out(tmp_path: Path) -> None:
    """`--root /tmp/ds` should read from /tmp/ds/combined/all_world.parquet
    and write to /tmp/ds/splits, when --source/--out are not passed."""
    import importlib.util

    script_path = Path(__file__).resolve().parents[2] / "scripts" / "split_parquets.py"
    spec = importlib.util.spec_from_file_location("split_parquets_cli", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    fake_root = tmp_path / "ds"
    _write_source_with_splits(fake_root / "combined" / "all_world.parquet")

    rc = module.main(["--root", str(fake_root)])
    assert rc == 0

    assert (fake_root / "splits" / "train.parquet").is_file()
    assert (fake_root / "splits" / "val.parquet").is_file()
    assert (fake_root / "splits" / "test.parquet").is_file()


def test_cli_explicit_source_out_overrides_root(tmp_path: Path) -> None:
    """`--source X` and `--out Y` take precedence over the --root default."""
    import importlib.util

    script_path = Path(__file__).resolve().parents[2] / "scripts" / "split_parquets.py"
    spec = importlib.util.spec_from_file_location("split_parquets_cli_overrides", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    source = tmp_path / "explicit_source.parquet"
    out = tmp_path / "explicit_out"
    _write_source_with_splits(source)

    rc = module.main([
        "--root", str(tmp_path / "ignored-root"),
        "--source", str(source),
        "--out", str(out),
    ])
    assert rc == 0

    assert (out / "train.parquet").is_file()
    # The --root default would have been tmp_path/ignored-root, but
    # nothing was written there because --source/--out were explicit.
    assert not (tmp_path / "ignored-root").exists()

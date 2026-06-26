"""Tests for whitelist module."""

import json
from pathlib import Path

import pytest

from osm_polygon_selection.stages.whitelist import (
    KEEP_LABEL,
    NOISE_CLUSTER_ID,
    NOISE_RESCUE_THRESHOLD,
    load_whitelist,
)


def _write_minimal_xlsx(path: Path, rows: list[dict]) -> None:
    """Write a minimal base_key_families.xlsx from rows."""
    import pandas as pd
    pd.DataFrame(rows).to_excel(path, index=False)


def _write_minimal_csv(path: Path, rows: list[dict], columns: list[str] | None = None) -> None:
    """Write a minimal CSV from rows. If rows is empty, write headers only."""
    import pandas as pd
    df = pd.DataFrame(rows, columns=columns)
    df.to_csv(path, index=False)


@pytest.fixture
def minimal_osm_stats(tmp_path: Path) -> Path:
    """Build a synthetic osm_stats root with one tfidf pipeline only.

    Two base keys, both 'yes':
      - landuse: 1 real-cluster tag (landuse=farmland), 1 noise tag with
        count_all >= threshold (landuse=forest, will be rescued)
      - building: 1 real-cluster tag (building=yes), 1 noise tag below
        threshold (building=typo, will NOT be rescued)
    Plus one 'no' base key to verify exclusion.
    """
    root = tmp_path / "osm_stats"
    tfidf = root / "tfidf"
    tfidf.mkdir(parents=True)

    _write_minimal_xlsx(
        tfidf / "base_key_families.xlsx",
        [
            {"keep": "yes", "base_key": "landuse"},
            {"keep": "yes", "base_key": "building"},
            {"keep": "no", "base_key": "excluded"},
        ],
    )

    _write_minimal_csv(
        tfidf / "cluster_memberships.csv",
        [
            # Real cluster (cluster_id != -1)
            {"cluster_id": 1, "base_key": "landuse", "key": "landuse",
             "value": "farmland", "feature": "landuse|farmland", "count_all": 1000},
            # Noise but high-volume (will be rescued)
            {"cluster_id": NOISE_CLUSTER_ID, "base_key": "landuse", "key": "landuse",
             "value": "forest", "feature": "landuse|forest", "count_all": 100_000},
            # Real cluster for building
            {"cluster_id": 2, "base_key": "building", "key": "building",
             "value": "yes", "feature": "building|yes", "count_all": 500},
            # Noise + low-volume (will NOT be rescued)
            {"cluster_id": NOISE_CLUSTER_ID, "base_key": "building", "key": "building",
             "value": "typo", "feature": "building|typo", "count_all": 10},
            # Excluded base key
            {"cluster_id": 3, "base_key": "excluded", "key": "excluded",
             "value": "whatever", "feature": "excluded|whatever", "count_all": 1000},
        ],
    )

    # Empty embeddings directory (load_whitelist should still work)
    (root / "embeddings").mkdir()
    _write_minimal_xlsx(root / "embeddings" / "base_key_families.xlsx", [])
    _write_minimal_csv(
        root / "embeddings" / "cluster_memberships_embeddings.csv",
        [],
        columns=["cluster_id", "base_key", "key", "value", "feature", "count_all"],
    )

    return root


def test_load_whitelist_returns_set(minimal_osm_stats: Path) -> None:
    result = load_whitelist(minimal_osm_stats)
    assert isinstance(result, set)


def test_load_whitelist_includes_real_cluster_tags(minimal_osm_stats: Path) -> None:
    result = load_whitelist(minimal_osm_stats)
    assert "landuse=farmland" in result
    assert "building=yes" in result


def test_load_whitelist_rescues_high_volume_noise(minimal_osm_stats: Path) -> None:
    result = load_whitelist(minimal_osm_stats)
    # landuse=forest is in noise but has count_all=100k >= threshold
    assert "landuse=forest" in result


def test_load_whitelist_drops_low_volume_noise(minimal_osm_stats: Path) -> None:
    result = load_whitelist(minimal_osm_stats)
    # building=typo is in noise with count_all=10 < threshold
    assert "building=typo" not in result


def test_load_whitelist_excludes_no_base_keys(minimal_osm_stats: Path) -> None:
    result = load_whitelist(minimal_osm_stats)
    assert "excluded=whatever" not in result


def test_load_whitelist_format_is_key_equals_value(minimal_osm_stats: Path) -> None:
    result = load_whitelist(minimal_osm_stats)
    for tag in result:
        assert "=" in tag
        k, _, v = tag.partition("=")
        assert k and v  # both non-empty


def test_load_whitelist_writes_json_when_out_path_given(
    minimal_osm_stats: Path, tmp_path: Path,
) -> None:
    out = tmp_path / "wl.json"
    result = load_whitelist(minimal_osm_stats, out_path=out)
    assert out.exists()
    loaded = json.loads(out.read_text())
    assert isinstance(loaded, list)
    assert set(loaded) == result


def test_load_whitelist_creates_output_parent_dir(
    minimal_osm_stats: Path, tmp_path: Path,
) -> None:
    out = tmp_path / "nested" / "subdir" / "wl.json"
    load_whitelist(minimal_osm_stats, out_path=out)
    assert out.exists()


def test_real_whitelist_loads_from_data_reference() -> None:
    """Integration test: real osm-stats files in data/reference/ load without error."""
    root = Path("data/reference/osm_stats")
    if not root.exists():
        pytest.skip("Real osm-stats files not present")
    result = load_whitelist(root)
    # Sanity: large set, contains obvious landuse tags
    assert len(result) > 1000
    assert "landuse=farmland" in result
    assert "building=yes" in result


def test_constants_have_sensible_values() -> None:
    """Document and guard the policy constants."""
    assert KEEP_LABEL == "yes"
    assert NOISE_CLUSTER_ID == -1
    assert NOISE_RESCUE_THRESHOLD > 0

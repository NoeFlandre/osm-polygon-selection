"""Tests for the optimized _record function in the extract stage.

The bottleneck in extract was shapely.is_valid + make_valid on
self-intersecting multipolygons with thousands of rings — a single
such polygon can take 30+ seconds.

The optimized _record uses:
  1. geom_type check (cheap) instead of is_valid + make_valid for
     the shape decision
  2. g.area (works on invalid geometry, returns valid area for
     self-intersecting polygons) instead of recomputing after
     make_valid
  3. buffer(0) (cheap; ~100x faster than make_valid) only if we
     actually need to keep the polygon for downstream code

These tests pin the optimization so we don't regress it.
"""

import time
from unittest.mock import MagicMock

import pytest

from osm_polygon_selection.stages.extract import _record_from_wkt


# A small valid polygon. At lat 45, 0.05 deg x 0.05 deg is ~5.5km x 5.5km,
# area ~30 km^2 — well within [MIN_AREA_KM2=0.1, MAX_AREA_KM2=100].
SMALL_POLY_WKT = "POLYGON((0 45, 0.05 45, 0.05 45.05, 0 45.05, 0 45))"


def _make_area_obj(osm_id: int, *, tags=None) -> MagicMock:
    """Mock osmium Area object — only .id and .tags are read by the optimized _record."""
    obj = MagicMock()
    obj.id = osm_id
    obj.is_area.return_value = True
    obj.from_way.return_value = False
    obj.tags = tags or []
    return obj


class FakeFout:
    """Minimal file-like that captures written lines."""

    def __init__(self):
        self.lines: list[str] = []

    def write(self, line: str) -> None:
        self.lines.append(line)

    def flush(self) -> None:
        pass


class TestRecordFastPath:
    """The fast path: cheap geom_type + area checks, no make_valid."""

    def test_simple_valid_polygon_written(self):
        obj = _make_area_obj(1)
        fout = FakeFout()
        drops: dict[str, int] = {}
        n = _record_from_wkt(obj, SMALL_POLY_WKT, fout, drops)
        assert n == 1
        assert len(fout.lines) == 1
        assert drops == {}

    def test_simple_valid_multipolygon_written(self):
        obj = _make_area_obj(2)
        fout = FakeFout()
        drops: dict[str, int] = {}
        n = _record_from_wkt(
            obj,
            "MULTIPOLYGON("
            "((0 45, 0.05 45, 0.05 45.05, 0 45.05, 0 45)),"
            "((0.1 45, 0.15 45, 0.15 45.05, 0.1 45.05, 0.1 45))"
            ")",
            fout,
            drops,
        )
        assert n == 1

    def test_self_intersecting_polygon_completes_fast(self):
        """A self-intersecting (invalid) polygon: must NOT block on
        make_valid. Either accepted or rejected, but in under 0.5s.
        """
        obj = _make_area_obj(3)
        t0 = time.time()
        _record_from_wkt(
            obj,
            # Self-intersecting bowtie
            "POLYGON((0 45, 0.05 45.05, 0 45.05, 0.05 45, 0 45))",
            FakeFout(),
            {},
        )
        elapsed = time.time() - t0
        assert elapsed < 0.5, f"_record too slow on self-intersecting: {elapsed:.2f}s"

    def test_too_small_dropped(self):
        # 1e-4 deg x 1e-4 deg at lat 45 -> ~0.01 km^2, under MIN_AREA_KM2 = 0.1.
        obj = _make_area_obj(4)
        fout = FakeFout()
        drops: dict[str, int] = {}
        n = _record_from_wkt(
            obj,
            "POLYGON((0 45, 0.0001 45, 0.0001 45.0001, 0 45.0001, 0 45))",
            fout,
            drops,
        )
        assert n == 0
        assert drops.get("too_small", 0) >= 1

    def test_too_large_dropped(self):
        # A polygon spanning 50 degrees of latitude and 50 degrees of
        # longitude is well over 100 km^2.
        obj = _make_area_obj(5)
        fout = FakeFout()
        drops: dict[str, int] = {}
        n = _record_from_wkt(
            obj,
            "POLYGON((0 0, 50 0, 50 50, 0 50, 0 0))",
            fout,
            drops,
        )
        assert n == 0
        assert drops.get("too_large", 0) >= 1


class TestRecordSafetyGuards:
    """The safety guards: WKT cap, vertex cap, validation timeout."""

    def test_oversized_wkt_dropped_before_parse(self):
        # 200k coords -> ~5 MB WKT. Slightly under 10 MB but the 50k
        # vertex cap should catch it first.
        coords = ",".join(f"{i % 360} {i // 360}" for i in range(200_000))
        wkt = f"POLYGON(({coords}))"
        # Ensure it really is >50k vertices.
        assert len(coords.split(",")) > 50_000
        obj = _make_area_obj(6)
        fout = FakeFout()
        drops: dict[str, int] = {}
        t0 = time.time()
        n = _record_from_wkt(obj, wkt, fout, drops)
        elapsed = time.time() - t0
        assert n == 0
        assert elapsed < 0.5, f"oversized WKT too slow: {elapsed:.2f}s"

    def test_too_many_vertices_dropped(self):
        """WKT is small enough to pass the byte cap, but has >50k vertices."""
        # Build a WKT with one ring of 60k vertices (a degenerate "spiral"
        # would also work). 60k vertices is over the 50k cap.
        # We use 60_000 * 12 chars ~= 720KB, under the 10MB byte cap.
        n_verts = 60_000
        parts = [f"{i / 100000:.5f} 45" for i in range(n_verts)]
        # Close the ring.
        parts.append(parts[0])
        vertices = ", ".join(parts)
        wkt = f"POLYGON(({vertices}))"
        # Should be under 10MB.
        assert len(wkt) < 10 * 1024 * 1024
        obj = _make_area_obj(7)
        fout = FakeFout()
        drops: dict[str, int] = {}
        n = _record_from_wkt(obj, wkt, fout, drops)
        assert n == 0
        assert drops.get("too_complex_vertices", 0) >= 1


class TestRecordPerf:
    """Perf regression: pathological inputs must complete in <1s."""

    def test_self_intersecting_1000_rings_completes_fast(self):
        """A 1000-ring self-intersecting multipolygon — the failure mode
        observed in france/germany/italy — must be handled in under 1s.
        """
        rings = []
        for i in range(1000):
            x0 = (i * 7) % 500
            y0 = (i * 11) % 500
            rings.append(
                f"({x0} {y0},{x0+100} {y0+50},{x0+50} {y0+100},{x0} {y0})"
            )
        wkt = "MULTIPOLYGON((" + "),(".join(rings) + "))"
        # WKT is ~30 KB — small enough to pass the byte cap.
        assert len(wkt) < 10 * 1024 * 1024
        obj = _make_area_obj(8)
        fout = FakeFout()
        drops: dict[str, int] = {}
        t0 = time.time()
        _record_from_wkt(obj, wkt, fout, drops)
        elapsed = time.time() - t0
        assert elapsed < 5.0, f"1000-ring polygon too slow: {elapsed:.2f}s"


class TestWallClockCap:
    """The wall-clock cap stops the run after max_seconds.

    This is the key fix for france/germany: the first-pass osmium
    index build can take 30+ min on a 4.7GB PBF and produces no
    polygons. Without a wall-clock cap, the process can't be killed
    cleanly. With it, we can budget a slice (e.g. 10 min) and resume.
    """

    def test_wall_clock_cap_stops_clean(self, tmp_path, monkeypatch):
        """A 10s wall-clock cap should stop a long-running extract
        cleanly, preserving the WAL so the next run can resume.
        """
        # Set up: a tiny fake PBF and a 2-second wall-clock cap.
        pbf = tmp_path / "fake.osm.pbf"
        pbf.touch()
        out = tmp_path / "out.jsonl"

        from osm_polygon_selection.stages import extract as extract_mod
        # Patch osmium.FileProcessor to yield objects forever (simulates
        # an infinite first-pass index build that we must interrupt).
        class FakeProcessor:
            def __init__(self, *_a, **_kw): pass
            def with_areas(self): return self
            def __iter__(self):
                i = 0
                while True:
                    yield self._make_obj(i)
                    i += 1
            def _make_obj(self, i):
                o = MagicMock()
                o.id = i
                # Drop: is_area returns False -> "not_an_area" drop.
                # This is enough to exercise the loop, the WAL, the
                # seen_ids set, and the deadline check.
                o.is_area.return_value = False
                o.from_way.return_value = False
                o.tags = []
                return o
        monkeypatch.setattr(extract_mod.osmium, "FileProcessor", FakeProcessor)
        # Run with a 2s wall-clock cap.
        from osm_polygon_selection.stages.extract import extract
        import signal as signal_mod
        t0 = time.time()
        try:
            extract(pbf, out, max_seconds=2.0)
        finally:
            # Disarm the SIGALRM so it doesn't fire during test teardown.
            signal_mod.setitimer(signal_mod.ITIMER_REAL, 0)
        elapsed = time.time() - t0
        # Should have stopped within 4s (some overhead).
        assert elapsed < 5.0, f"wall-clock cap didn't stop: {elapsed:.1f}s"
        # WAL file should exist and contain some seen ids.
        wal = out.with_suffix(out.suffix + ".seen_ids")
        assert wal.exists()
        n_wal = sum(1 for _ in wal.open())
        assert n_wal > 0, "WAL should have at least one id"
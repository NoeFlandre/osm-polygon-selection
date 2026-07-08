"""Shared helpers for readme tests."""

from __future__ import annotations


def _country(name: str, n: int, status: str = "clean") -> dict:
    return {"country": name, "n_polygons": n, "extract_status": status}


def _manifest(countries: list[dict], total: int | None = None) -> dict:
    if total is None:
        total = sum(c["n_polygons"] for c in countries)
    return {
        "version": "v0.1.0",
        "git_sha": "abc1234",
        "built_at": "2026-07-01T00:00:00",
        "total_polygons": total,
        "n_countries": len(countries),
        "countries": countries,
        "schema": [
            "osm_id", "osm_type", "centroid_lon", "centroid_lat", "area_km2",
            "tags", "matched_tag", "continent", "size_bin", "country",
            "extract_status", "pbf_date", "geometry_wkt",
        ],
    }

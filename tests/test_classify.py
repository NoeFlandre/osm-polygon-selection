"""Tests for Stage 4 classify module."""

from osm_polygon_selection.classify import size_bin


def test_size_bin_tiny():
    assert size_bin(0.001) == "tiny"
    assert size_bin(0.05) == "tiny"
    assert size_bin(0.099) == "tiny"


def test_size_bin_small():
    assert size_bin(0.1) == "small"
    assert size_bin(0.5) == "small"
    assert size_bin(0.999) == "small"


def test_size_bin_medium():
    assert size_bin(1.0) == "medium"
    assert size_bin(5.0) == "medium"
    assert size_bin(9.999) == "medium"


def test_size_bin_large():
    assert size_bin(10.0) == "large"
    assert size_bin(50.0) == "large"
    assert size_bin(100.0) == "large"
    assert size_bin(1_000_000.0) == "large"

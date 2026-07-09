"""Smoke tests for the cli/ modules.

Each cli module is canonical for one script. The tests here only
pin the public surface (build_parser + main) and verify the
parsers accept the documented arguments.
"""

from __future__ import annotations

from pathlib import Path

import pytest


class TestBuildDatasetCLI:
    def test_module_imports(self) -> None:
        from osm_polygon_selection.cli import build_dataset
        assert hasattr(build_dataset, "main")

    def test_main_calls_runner(self) -> None:
        """main() delegates to dataset_build.runner.run_build_dataset."""
        from osm_polygon_selection.cli.build_dataset import main
        import inspect
        src = inspect.getsource(main)
        assert "run_build_dataset" in src


class TestMakeSplitCLI:
    def test_module_imports(self) -> None:
        from osm_polygon_selection.cli import make_split
        assert hasattr(make_split, "build_parser")
        assert hasattr(make_split, "main")

    def test_parser_defaults(self) -> None:
        from osm_polygon_selection.cli.make_split import build_parser
        args = build_parser().parse_args([])
        assert args.train > 0
        assert args.val > 0
        assert args.test > 0

    def test_parser_ratios(self) -> None:
        from osm_polygon_selection.cli.make_split import build_parser
        args = build_parser().parse_args(
            ["--train", "0.7", "--val", "0.2", "--test", "0.1"]
        )
        assert args.train == 0.7
        assert args.val == 0.2
        assert args.test == 0.1


class TestSampleForMapCLI:
    def test_module_imports(self) -> None:
        from osm_polygon_selection.cli import sample_for_map
        assert hasattr(sample_for_map, "main")


class TestSplitParquetsCLI:
    def test_module_imports(self) -> None:
        from osm_polygon_selection.cli import split_parquets
        assert hasattr(split_parquets, "build_parser")
        assert hasattr(split_parquets, "main")

    def test_parser_root_only(self) -> None:
        from osm_polygon_selection.cli.split_parquets import build_parser
        args = build_parser().parse_args([])
        assert args.root is not None
        assert args.source is None
        assert args.out is None


class TestOrganizeDatasetCLI:
    def test_module_imports(self) -> None:
        from osm_polygon_selection.cli import organize_dataset
        assert hasattr(organize_dataset, "build_parser")
        assert hasattr(organize_dataset, "main")


class TestStage0ExtractCLI:
    def test_module_imports(self) -> None:
        from osm_polygon_selection.cli import stage0_extract
        assert hasattr(stage0_extract, "build_parser")
        assert hasattr(stage0_extract, "main")

    def test_parser_pbf_and_out(self, tmp_path: Path) -> None:
        from osm_polygon_selection.cli.stage0_extract import build_parser
        args = build_parser().parse_args([str(tmp_path / "in.pbf"), str(tmp_path / "out.jsonl")])
        assert args.pbf == tmp_path / "in.pbf"
        assert args.out == tmp_path / "out.jsonl"
        assert args.limit is None
        assert args.max_seconds is None

    def test_parser_with_limit(self, tmp_path: Path) -> None:
        from osm_polygon_selection.cli.stage0_extract import build_parser
        args = build_parser().parse_args(
            [str(tmp_path / "in.pbf"), str(tmp_path / "out.jsonl"),
             "--limit", "1000", "--max-seconds", "30"]
        )
        assert args.limit == 1000
        assert args.max_seconds == 30


class TestStage1BuildWhitelistCLI:
    def test_module_imports(self) -> None:
        from osm_polygon_selection.cli import stage1_build_whitelist
        assert hasattr(stage1_build_whitelist, "build_parser")
        assert hasattr(stage1_build_whitelist, "main")


class TestStage2FilterCLI:
    def test_module_imports(self) -> None:
        from osm_polygon_selection.cli import stage2_filter
        assert hasattr(stage2_filter, "build_parser")
        assert hasattr(stage2_filter, "main")


class TestStage3ClassifyCLI:
    def test_module_imports(self) -> None:
        from osm_polygon_selection.cli import stage3_classify
        assert hasattr(stage3_classify, "build_parser")
        assert hasattr(stage3_classify, "main")


class TestVisualizeCLI:
    def test_module_imports(self) -> None:
        from osm_polygon_selection.cli import visualize
        assert hasattr(visualize, "build_parser")
        assert hasattr(visualize, "main")


class TestUploadToHfCLI:
    def test_module_imports(self) -> None:
        from osm_polygon_selection.cli import upload_to_hf
        assert hasattr(upload_to_hf, "build_parser")
        assert hasattr(upload_to_hf, "main")
        assert hasattr(upload_to_hf, "upload_to_hf")

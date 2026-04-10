import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from arwiz.cli import cli
from arwiz.foundation import (
    BranchCoverage,
    BranchInfo,
    HotSpot,
    OptimizationAttempt,
    OptimizationResult,
    ProfileResult,
)
from click.testing import CliRunner

FIXTURES = Path(__file__).parent.parent / "fixtures" / "targets"
SIMPLE_LOOP = str(FIXTURES / "simple_loop.py")


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def fake_profile_result():
    return ProfileResult(
        script_path=SIMPLE_LOOP,
        duration_ms=42.5,
    )


@pytest.fixture
def fake_hotspots():
    return [
        HotSpot(
            function_name="compute_sum",
            file_path=SIMPLE_LOOP,
            line_range=(10, 15),
            cumulative_time_ms=40.0,
            self_time_ms=38.0,
            call_count=1,
        ),
    ]


@pytest.fixture
def fake_branch_coverage():
    return BranchCoverage(
        total_branches=4,
        covered_branches=3,
        coverage_percent=75.0,
        uncovered_lines=[7],
        branch_details=[
            BranchInfo(
                line_number=10,
                branch_type="for",
                condition="for x in data",
                taken=True,
            ),
            BranchInfo(
                line_number=13,
                branch_type="if",
                condition="result += x * x",
                taken=True,
            ),
        ],
        script_path=SIMPLE_LOOP,
        duration_ms=12.0,
    )


@pytest.fixture
def fake_optimization():
    return OptimizationAttempt(
        attempt_id="tmpl_numpy_vectorize",
        original_code=(
            "def compute_sum(data):\n    result = 0.0\n"
            "    for x in data:\n        result += x * x\n    return result"
        ),
        optimized_code=(
            "import numpy as np\ndef compute_sum(data):\n"
            "    return float(np.sum(np.array(data) ** 2))"
        ),
        strategy="template",
        template_name="numpy_vectorize",
        syntax_valid=True,
    )


class TestProfileCommand:
    @patch("arwiz.cli.commands.profile_cmd.DefaultHotspotDetector")
    @patch("arwiz.cli.commands.profile_cmd.DefaultProfiler")
    def test_profile_text_output(
        self, mock_profiler_cls, mock_hotspot_cls, runner, fake_profile_result
    ):
        mock_profiler = MagicMock()
        mock_profiler.profile_script.return_value = fake_profile_result
        mock_profiler_cls.return_value = mock_profiler

        mock_hotspot = MagicMock()
        mock_hotspot.detect_hotspots.return_value = []
        mock_hotspot_cls.return_value = mock_hotspot

        result = runner.invoke(cli, ["profile", SIMPLE_LOOP])

        assert result.exit_code == 0
        assert "42.50ms" in result.output
        mock_profiler.profile_script.assert_called_once()

    @patch("arwiz.cli.commands.profile_cmd.DefaultHotspotDetector")
    @patch("arwiz.cli.commands.profile_cmd.DefaultProfiler")
    def test_profile_json_format(
        self, mock_profiler_cls, mock_hotspot_cls, runner, fake_profile_result
    ):
        mock_profiler = MagicMock()
        mock_profiler.profile_script.return_value = fake_profile_result
        mock_profiler_cls.return_value = mock_profiler

        mock_hotspot = MagicMock()
        mock_hotspot.detect_hotspots.return_value = []
        mock_hotspot_cls.return_value = mock_hotspot

        result = runner.invoke(cli, ["profile", SIMPLE_LOOP, "--format", "json"])

        assert result.exit_code == 0
        assert "duration_ms" in result.output
        assert "42.5" in result.output or "42.50" in result.output

    @patch("arwiz.cli.commands.profile_cmd.DefaultHotspotDetector")
    @patch("arwiz.cli.commands.profile_cmd.DefaultProfiler")
    def test_profile_with_args(
        self, mock_profiler_cls, mock_hotspot_cls, runner, fake_profile_result
    ):
        mock_profiler = MagicMock()
        mock_profiler.profile_script.return_value = fake_profile_result
        mock_profiler_cls.return_value = mock_profiler

        mock_hotspot = MagicMock()
        mock_hotspot.detect_hotspots.return_value = []
        mock_hotspot_cls.return_value = mock_hotspot

        result = runner.invoke(cli, ["profile", SIMPLE_LOOP, "foo", "bar"])

        assert result.exit_code == 0
        call_args = mock_profiler.profile_script.call_args
        assert call_args[1]["args"] == ["foo", "bar"]

    def test_profile_missing_script(self, runner):
        result = runner.invoke(cli, ["profile", "/nonexistent/script.py"])
        # With nargs=-1, the CLI proceeds but profiling fails gracefully
        assert result.exit_code == 0
        assert "nonexistent" in result.output or "error" in result.output.lower()


class TestOptimizeCommand:
    @patch("arwiz.cli.commands.optimize_cmd.DefaultOrchestrator")
    def test_optimize_template_strategy(
        self,
        mock_orch_cls,
        runner,
        fake_optimization,
    ):
        mock_orch = MagicMock()
        mock_orch.run_profile_optimize_pipeline.return_value = OptimizationResult(
            function_name="compute_sum",
            file_path=SIMPLE_LOOP,
            attempts=[fake_optimization],
            best_attempt=fake_optimization,
            applied=True,
            total_time_saved_ms=0.0,
        )
        mock_orch_cls.return_value = mock_orch

        result = runner.invoke(
            cli, ["optimize", SIMPLE_LOOP, "--function", "compute_sum", "--strategy", "template"]
        )

        assert result.exit_code == 0
        assert "numpy_vectorize" in result.output

    @patch("arwiz.cli.commands.optimize_cmd.DefaultOrchestrator")
    def test_optimize_auto_strategy(
        self,
        mock_orch_cls,
        runner,
        fake_optimization,
    ):
        mock_orch = MagicMock()
        mock_orch.run_profile_optimize_pipeline.return_value = OptimizationResult(
            function_name="compute_sum",
            file_path=SIMPLE_LOOP,
            attempts=[fake_optimization],
            best_attempt=fake_optimization,
            applied=True,
            total_time_saved_ms=0.0,
        )
        mock_orch_cls.return_value = mock_orch

        result = runner.invoke(
            cli, ["optimize", SIMPLE_LOOP, "--function", "compute_sum", "--strategy", "auto"]
        )

        assert result.exit_code == 0

    @patch("arwiz.cli.commands.optimize_cmd.DefaultOrchestrator")
    def test_optimize_function_not_found(self, mock_orch_cls, runner):
        mock_orch = MagicMock()
        mock_orch.run_profile_optimize_pipeline.return_value = OptimizationResult(
            function_name="nonexistent",
            file_path=SIMPLE_LOOP,
            attempts=[
                OptimizationAttempt(
                    attempt_id="opt_err",
                    original_code="",
                    optimized_code="",
                    strategy="auto",
                    error_message="Function 'nonexistent' not found in detected hotspots",
                )
            ],
            best_attempt=None,
            applied=False,
            total_time_saved_ms=0.0,
        )
        mock_orch_cls.return_value = mock_orch

        result = runner.invoke(cli, ["optimize", SIMPLE_LOOP, "--function", "nonexistent"])

        assert result.exit_code == 0
        assert "not found" in result.output

    @patch("arwiz.cli.commands.optimize_cmd.DefaultOrchestrator")
    def test_optimize_without_function_warns(self, mock_orch_cls, runner):
        mock_orch = MagicMock()
        mock_orch.run_profile_optimize_pipeline.return_value = OptimizationResult(
            function_name="pytest",
            file_path="pytest",
            attempts=[
                OptimizationAttempt(
                    attempt_id="opt_err",
                    original_code="",
                    optimized_code="",
                    strategy="auto",
                    error_message="Function extraction is only supported for Python scripts (.py files)",
                )
            ],
            best_attempt=None,
            applied=False,
            total_time_saved_ms=0.0,
        )
        mock_orch_cls.return_value = mock_orch

        result = runner.invoke(cli, ["optimize", "pytest"])

        assert result.exit_code == 0
        assert ".py" in result.output


class TestCoverageCommand:
    @patch("arwiz.cli.commands.coverage_cmd.DefaultCoverageTracer")
    def test_coverage_basic(self, mock_tracer_cls, runner, fake_branch_coverage):
        mock_tracer = MagicMock()
        mock_tracer.trace_branches.return_value = fake_branch_coverage
        mock_tracer_cls.return_value = mock_tracer

        result = runner.invoke(cli, ["coverage", SIMPLE_LOOP])

        assert result.exit_code == 0
        assert "75.0%" in result.output
        mock_tracer.trace_branches.assert_called_once()

    @patch("arwiz.cli.commands.coverage_cmd.DefaultCoverageTracer")
    def test_coverage_store_inputs_flag(self, mock_tracer_cls, runner, fake_branch_coverage):
        mock_tracer = MagicMock()
        mock_tracer.trace_branches.return_value = fake_branch_coverage
        mock_tracer_cls.return_value = mock_tracer

        result = runner.invoke(cli, ["coverage", SIMPLE_LOOP, "--store-inputs"])

        assert result.exit_code == 0
        assert "Input storage" in result.output

    @patch("arwiz.cli.commands.coverage_cmd.DefaultCoverageTracer")
    def test_coverage_with_args(self, mock_tracer_cls, runner, fake_branch_coverage):
        mock_tracer = MagicMock()
        mock_tracer.trace_branches.return_value = fake_branch_coverage
        mock_tracer_cls.return_value = mock_tracer

        result = runner.invoke(cli, ["coverage", SIMPLE_LOOP, "x", "y"])

        assert result.exit_code == 0
        call_args = mock_tracer.trace_branches.call_args
        assert call_args[1]["args"] == ["x", "y"]


class TestReportCommand:
    def test_report_text_format(self, runner, tmp_path):
        profile_data = {
            "profile_id": "prof_test_123",
            "script_path": SIMPLE_LOOP,
            "duration_ms": 42.5,
            "hotspots": [
                {
                    "function_name": "compute_sum",
                    "self_time_ms": 38.0,
                    "call_count": 1,
                    "file_path": SIMPLE_LOOP,
                    "line_range": [10, 15],
                }
            ],
        }
        profile_file = tmp_path / "profile.json"
        profile_file.write_text(json.dumps(profile_data))

        result = runner.invoke(cli, ["report", str(profile_file)])

        assert result.exit_code == 0
        assert "prof_test_123" in result.output
        assert "compute_sum" in result.output

    def test_report_json_format(self, runner, tmp_path):
        profile_data = {
            "profile_id": "prof_json_test",
            "script_path": SIMPLE_LOOP,
            "duration_ms": 10.0,
            "hotspots": [],
        }
        profile_file = tmp_path / "profile.json"
        profile_file.write_text(json.dumps(profile_data))

        result = runner.invoke(cli, ["report", str(profile_file), "--format", "json"])

        assert result.exit_code == 0

    def test_report_html_format(self, runner, tmp_path):
        profile_data = {
            "profile_id": "prof_html_test",
            "script_path": SIMPLE_LOOP,
            "duration_ms": 10.0,
            "hotspots": [],
        }
        profile_file = tmp_path / "profile.json"
        profile_file.write_text(json.dumps(profile_data))

        result = runner.invoke(cli, ["report", str(profile_file), "--format", "html"])

        assert result.exit_code == 0
        assert "<html>" in result.output

    def test_report_missing_file(self, runner):
        result = runner.invoke(cli, ["report", "/nonexistent/profile.json"])
        assert result.exit_code != 0

    def test_report_invalid_json(self, runner, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json at all")

        result = runner.invoke(cli, ["report", str(bad_file)])
        assert result.exit_code != 0


class TestCliGroup:
    def test_cli_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "profile" in result.output
        assert "optimize" in result.output
        assert "coverage" in result.output
        assert "report" in result.output

    def test_cli_version(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0

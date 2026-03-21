"""Integration tests for Coverage -> Replay pipeline.

Tests the orchestrator's run_coverage_replay_pipeline method
with mocked subprocess execution.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from arwiz.coverage_tracer.ast_analyzer import get_static_branches
from arwiz.foundation import BranchCoverage
from arwiz.orchestrator.core import DefaultOrchestrator
from arwiz.process_manager.core import ProcessResult

BRANCHING_PATH = "test/fixtures/targets/branching.py"
SIMPLE_LOOP_PATH = "test/fixtures/targets/simple_loop.py"


def _make_process_result(traced_lines: list[int]) -> ProcessResult:
    """Build a fake ProcessResult with traced line output."""
    stdout = f"some stdout\n__ARWIZ_TRACE_SEP__\n{json.dumps(sorted(traced_lines))}\n"
    return ProcessResult(
        exit_code=0,
        stdout=stdout,
        stderr="",
        duration_ms=10.0,
    )


@pytest.fixture()
def mock_tracer():
    """Create a DefaultCoverageTracer with mocked process_manager."""
    from arwiz.coverage_tracer import DefaultCoverageTracer

    tracer = DefaultCoverageTracer()
    tracer._process_manager = MagicMock()
    return tracer


@pytest.mark.integration
class TestCoverageReplayPipeline:
    """Tests for run_coverage_replay_pipeline."""

    def test_successful_branch_tracing_branching_py(
        self,
        mock_tracer,
    ) -> None:
        """Pipeline completes with 100%% coverage when all lines traced."""
        static = get_static_branches(BRANCHING_PATH)
        traced_lines = [ln for ln, _ in static]
        mock_tracer._process_manager.run_script.return_value = _make_process_result(traced_lines)

        orchestrator = DefaultOrchestrator(coverage_tracer=mock_tracer)
        result = orchestrator.run_coverage_replay_pipeline(
            script_path=BRANCHING_PATH,
        )

        assert isinstance(result, BranchCoverage)
        assert result.total_branches == len(static)
        assert result.covered_branches == result.total_branches
        assert result.coverage_percent == 100.0
        assert len(result.uncovered_lines) == 0
        assert result.script_path == BRANCHING_PATH
        assert result.duration_ms >= 0
        assert len(result.branch_details) == result.total_branches

    def test_coverage_percentage_calculated_correctly(
        self,
        mock_tracer,
    ) -> None:
        """Coverage percent reflects actual covered vs total branches."""
        static = get_static_branches(BRANCHING_PATH)
        all_lines = sorted({ln for ln, _ in static})
        unique_lines = all_lines[: len(all_lines) // 2]
        mock_tracer._process_manager.run_script.return_value = _make_process_result(unique_lines)

        orchestrator = DefaultOrchestrator(coverage_tracer=mock_tracer)
        result = orchestrator.run_coverage_replay_pipeline(
            script_path=BRANCHING_PATH,
        )

        expected_covered = sum(1 for ln, _ in static if ln in set(unique_lines))
        expected_pct = round(expected_covered / len(static) * 100, 2)
        assert result.coverage_percent == expected_pct
        assert result.total_branches == len(static)
        assert result.covered_branches == expected_covered

    def test_uncovered_branches_identified(
        self,
        mock_tracer,
    ) -> None:
        """Uncovered branches appear in uncovered_lines and BranchInfo."""
        static = get_static_branches(BRANCHING_PATH)
        traced = [static[0][0]]
        mock_tracer._process_manager.run_script.return_value = _make_process_result(traced)

        orchestrator = DefaultOrchestrator(coverage_tracer=mock_tracer)
        result = orchestrator.run_coverage_replay_pipeline(
            script_path=BRANCHING_PATH,
        )

        uncovered_expected = [ln for ln, _ in static[1:]]
        assert set(result.uncovered_lines) == set(uncovered_expected)

        uncovered_details = [b for b in result.branch_details if not b.taken]
        assert len(uncovered_details) == len(uncovered_expected)

        covered_details = [b for b in result.branch_details if b.taken]
        assert len(covered_details) == 1
        assert covered_details[0].line_number == traced[0]

    def test_pipeline_handles_tracer_errors_gracefully(
        self,
        mock_tracer,
    ) -> None:
        """Pipeline propagates errors from the coverage tracer."""
        mock_tracer.trace_branches = MagicMock(
            side_effect=RuntimeError("Tracer subprocess failed"),
        )

        orchestrator = DefaultOrchestrator(coverage_tracer=mock_tracer)
        with pytest.raises(RuntimeError, match="Tracer subprocess failed"):
            orchestrator.run_coverage_replay_pipeline(
                script_path=BRANCHING_PATH,
            )

    def test_pipeline_handles_minimal_branch_script(
        self,
        mock_tracer,
    ) -> None:
        """Pipeline works correctly with simple_loop.py (minimal branches)."""
        traced_lines = [13, 28]
        mock_tracer._process_manager.run_script.return_value = _make_process_result(traced_lines)

        orchestrator = DefaultOrchestrator(coverage_tracer=mock_tracer)
        result = orchestrator.run_coverage_replay_pipeline(
            script_path=SIMPLE_LOOP_PATH,
        )

        assert isinstance(result, BranchCoverage)
        assert result.total_branches == 2
        assert result.covered_branches == 2
        assert result.coverage_percent == 100.0
        assert result.script_path == SIMPLE_LOOP_PATH

    def test_branch_coverage_data_structure_fields(
        self,
        mock_tracer,
    ) -> None:
        """BranchCoverage and BranchInfo have all expected fields."""
        mock_tracer._process_manager.run_script.return_value = _make_process_result([])

        orchestrator = DefaultOrchestrator(coverage_tracer=mock_tracer)
        result = orchestrator.run_coverage_replay_pipeline(
            script_path=BRANCHING_PATH,
        )

        for field in (
            "total_branches",
            "covered_branches",
            "coverage_percent",
            "uncovered_lines",
            "branch_details",
            "script_path",
            "duration_ms",
        ):
            assert hasattr(result, field), f"Missing field: {field}"

        for detail in result.branch_details:
            assert isinstance(detail.line_number, int)
            assert isinstance(detail.branch_type, str)
            assert isinstance(detail.condition, str)
            assert isinstance(detail.taken, bool)

    def test_pipeline_state_tracks_coverage_steps(
        self,
        mock_tracer,
    ) -> None:
        """Pipeline state records load_config, trace_branches, and
        get_uncovered_branches steps."""
        static = get_static_branches(BRANCHING_PATH)
        mock_tracer._process_manager.run_script.return_value = _make_process_result(
            [ln for ln, _ in static]
        )

        orchestrator = DefaultOrchestrator(coverage_tracer=mock_tracer)
        orchestrator.run_coverage_replay_pipeline(
            script_path=BRANCHING_PATH,
        )

        state = orchestrator.last_pipeline_state
        assert state is not None
        assert state.pipeline_type == "coverage_replay"
        step_names = [s.name for s in state.steps]
        assert "load_config" in step_names
        assert "trace_branches" in step_names
        assert "get_uncovered_branches" in step_names

    def test_partial_coverage_with_branching_py(
        self,
        mock_tracer,
    ) -> None:
        """Partial coverage returns correct uncovered branch types."""
        static = get_static_branches(BRANCHING_PATH)
        traced_line_set = {11, 13, 15, 17}
        mock_tracer._process_manager.run_script.return_value = _make_process_result(
            list(traced_line_set)
        )

        orchestrator = DefaultOrchestrator(coverage_tracer=mock_tracer)
        result = orchestrator.run_coverage_replay_pipeline(
            script_path=BRANCHING_PATH,
        )

        expected_covered = sum(1 for ln, _ in static if ln in traced_line_set)
        assert result.covered_branches == expected_covered
        assert len(result.uncovered_lines) == len(static) - expected_covered
        for detail in result.branch_details:
            assert detail.branch_type in (
                "if",
                "elif",
                "else",
                "for",
                "while",
                "try",
                "except",
            )

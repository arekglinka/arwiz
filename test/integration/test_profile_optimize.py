"""Integration tests for the Profile -> Optimize pipeline.

Tests DefaultOrchestrator.run_profile_optimize_pipeline end-to-end
with real target fixtures and mocked subprocess-heavy components.
"""

from pathlib import Path

import pytest
from arwiz.foundation import (
    ArwizConfig,
    HotSpot,
    OptimizationResult,
    ProfileResult,
)
from arwiz.orchestrator import DefaultOrchestrator

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "targets"
SIMPLE_LOOP = str(FIXTURES / "simple_loop.py")
BRANCHING = str(FIXTURES / "branching.py")


class DummyConfigLoader:
    def load_config(self, config_path=None):  # noqa: ANN001, ARG002
        return ArwizConfig()


class DummyProfiler:
    def __init__(
        self,
        script_path: str,
        should_fail: bool = False,
    ) -> None:
        self._script_path = script_path
        self._should_fail = should_fail

    def profile_script(self, script_path, args=None, config=None):  # noqa: ANN001, ARG002
        if self._should_fail:
            msg = "profiling subprocess failed"
            raise RuntimeError(msg)
        return ProfileResult(
            script_path=str(script_path),
            duration_ms=120.0,
        )


class DummyHotspotDetector:
    def __init__(self, hotspots: list[HotSpot]) -> None:
        self._hotspots = hotspots

    def detect_hotspots(self, profile_result, threshold_pct=5.0):  # noqa: ANN001, ARG002
        return self._hotspots

    def rank_by_impact(self, hotspots):  # noqa: ANN001
        return hotspots


class DummyTemplateOptimizer:
    def __init__(self, optimized_source: str) -> None:
        self._optimized = optimized_source

    def detect_applicable_templates(
        self,
        source_code: str,
        hotspot=None,  # noqa: ANN001
    ) -> list[str]:
        return ["vectorize_loop"]

    def apply_template(self, source_code: str, template_name: str) -> str:  # noqa: ARG002
        return self._optimized

    def list_templates(self) -> list[str]:
        return ["vectorize_loop"]


class DummyEquivalenceChecker:
    def __init__(self, equivalent: bool = True, reason: str = "") -> None:
        self._equivalent = equivalent
        self._reason = reason

    def check_equivalence(self, original, optimized, tolerance=1e-6):  # noqa: ANN001, ARG002
        return self._equivalent, self._reason


def _make_hotspot(function_name: str, script_path: str) -> HotSpot:
    return HotSpot(
        function_name=function_name,
        file_path=script_path,
        line_range=(10, 15),
        cumulative_time_ms=80.0,
        self_time_ms=75.0,
        call_count=10,
    )


def _orchestrator(
    script_path: str,
    function_name: str,
    *,
    profiler_fail: bool = False,
    hotspots: list[HotSpot] | None = None,
    template_source: str | None = None,
    equiv_result: tuple[bool, str] | None = None,
) -> DefaultOrchestrator:
    """Build a DefaultOrchestrator with all subprocess deps mocked."""
    profiler = DummyProfiler(script_path, should_fail=profiler_fail)
    hs = hotspots if hotspots is not None else [_make_hotspot(function_name, script_path)]

    kwargs: dict = {
        "config_loader": DummyConfigLoader(),
        "profiler": profiler,
        "hotspot_detector": DummyHotspotDetector(hs),
    }

    if template_source is not None:
        kwargs["template_optimizer"] = DummyTemplateOptimizer(template_source)
    if equiv_result is not None:
        kwargs["equivalence_checker"] = DummyEquivalenceChecker(*equiv_result)

    orch = DefaultOrchestrator(**kwargs)

    if equiv_result is not None:
        orch._check_equivalence = lambda *a, **kw: equiv_result  # noqa: SLF001

    return orch


@pytest.mark.integration
class TestProfileOptimizePipeline:
    def test_successful_template_optimization_simple_loop(self) -> None:
        """Given simple_loop.py with compute_sum, when template strategy
        runs, then pipeline completes with applied=True.
        """
        result = _orchestrator(
            SIMPLE_LOOP,
            "compute_sum",
            template_source=("def compute_sum(data):\n    return sum(x * x for x in data)\n"),
            equiv_result=(True, ""),
        ).run_profile_optimize_pipeline(
            script_path=SIMPLE_LOOP,
            function_name="compute_sum",
            strategy="template",
        )

        assert isinstance(result, OptimizationResult)
        assert result.function_name == "compute_sum"
        assert result.file_path == SIMPLE_LOOP
        assert len(result.attempts) == 1
        assert result.attempts[0].strategy == "template"
        assert result.attempts[0].syntax_valid is True
        assert result.attempts[0].passed_equivalence is True
        assert result.best_attempt is not None
        assert result.applied is True

    def test_template_optimization_hotspot_found(self) -> None:
        """When classify_value is in hotspots, then template
        succeeds with passed_equivalence=True.
        """
        hs = [_make_hotspot("classify_value", BRANCHING)]
        result = _orchestrator(
            BRANCHING,
            "classify_value",
            hotspots=hs,
            template_source=(
                "def classify_value(x):\n    return 'negative' if x < 0 else 'non-negative'\n"
            ),
            equiv_result=(True, ""),
        ).run_profile_optimize_pipeline(
            script_path=BRANCHING,
            function_name="classify_value",
            strategy="template",
        )

        assert result.function_name == "classify_value"
        assert result.attempts[0].strategy == "template"
        assert result.attempts[0].passed_equivalence is True
        assert result.best_attempt is not None

    def test_rollback_when_equivalence_fails(self) -> None:
        """When optimized code fails equivalence, then applied=False
        and best_attempt is None.
        """
        result = _orchestrator(
            SIMPLE_LOOP,
            "compute_sum",
            template_source=("def compute_sum(data):\n    return 0  # intentionally wrong\n"),
            equiv_result=(False, "Outputs differ: expected 0.0, got 0"),
        ).run_profile_optimize_pipeline(
            script_path=SIMPLE_LOOP,
            function_name="compute_sum",
            strategy="template",
        )

        assert result.applied is False
        assert result.best_attempt is None
        assert len(result.attempts) == 1
        assert result.attempts[0].syntax_valid is True
        assert result.attempts[0].passed_equivalence is False
        assert result.attempts[0].error_message == "Outputs differ: expected 0.0, got 0"

    def test_error_handling_profiling_fails(self) -> None:
        """Pipeline returns error result when profiler raises."""
        result = _orchestrator(
            SIMPLE_LOOP,
            "compute_sum",
            profiler_fail=True,
        ).run_profile_optimize_pipeline(
            script_path=SIMPLE_LOOP,
            function_name="compute_sum",
            strategy="template",
        )

        assert result.applied is False
        assert result.best_attempt is None
        assert len(result.attempts) == 1
        assert "profiling subprocess failed" in (result.attempts[0].error_message or "")
        assert "Pipeline failed before optimization" in (result.attempts[0].error_message or "")

    def test_error_handling_function_not_in_hotspots(self) -> None:
        """Pipeline returns error when function missing from hotspots."""
        wrong_hs = [_make_hotspot("nonexistent_func", SIMPLE_LOOP)]
        result = _orchestrator(
            SIMPLE_LOOP,
            "compute_sum",
            hotspots=wrong_hs,
        ).run_profile_optimize_pipeline(
            script_path=SIMPLE_LOOP,
            function_name="compute_sum",
            strategy="template",
        )

        assert result.applied is False
        assert result.best_attempt is None
        assert "not found in detected hotspots" in (result.attempts[0].error_message or "")

    def test_syntax_error_in_generated_code(self) -> None:
        """Pipeline catches syntax errors from the template optimizer."""
        result = _orchestrator(
            SIMPLE_LOOP,
            "compute_sum",
            template_source="def compute_sum(data:\n    return data  # missing paren\n",
        ).run_profile_optimize_pipeline(
            script_path=SIMPLE_LOOP,
            function_name="compute_sum",
            strategy="template",
        )

        assert result.applied is False
        assert result.best_attempt is None
        assert result.attempts[0].syntax_valid is False
        assert result.attempts[0].passed_equivalence is False
        assert result.attempts[0].error_message is not None
        assert "never closed" in (result.attempts[0].error_message or "")

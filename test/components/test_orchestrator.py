from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPONENTS_DIR = ROOT / "components"
if str(COMPONENTS_DIR) not in sys.path:
    sys.path.insert(0, str(COMPONENTS_DIR))

foundation = import_module("arwiz.foundation")
orchestrator_module = import_module("arwiz.orchestrator")
pipeline_module = import_module("arwiz.orchestrator.pipeline_state")

ArwizConfig = foundation.ArwizConfig
BranchCoverage = foundation.BranchCoverage
BranchInfo = foundation.BranchInfo
HotSpot = foundation.HotSpot
OptimizationAttempt = foundation.OptimizationAttempt
ProfileResult = foundation.ProfileResult

DefaultOrchestrator = orchestrator_module.DefaultOrchestrator
PipelineState = pipeline_module.PipelineState
PipelineStep = pipeline_module.PipelineStep


def _write_script(tmp_path: Path, source: str) -> Path:
    script = tmp_path / "target.py"
    script.write_text(source, encoding="utf-8")
    return script


def _profile_result(script_path: Path) -> ProfileResult:
    return ProfileResult(script_path=str(script_path), duration_ms=100.0)


def _hotspot(function_name: str, script_path: Path) -> HotSpot:
    return HotSpot(
        function_name=function_name,
        file_path=str(script_path),
        line_range=(1, 3),
        cumulative_time_ms=80.0,
        self_time_ms=75.0,
        call_count=10,
    )


class DummyConfigLoader:
    def load_config(self, config_path=None) -> ArwizConfig:  # noqa: ANN001, ARG002
        return ArwizConfig()


class DummyProfiler:
    def __init__(
        self, profile_result: ProfileResult | None = None, should_fail: bool = False
    ) -> None:
        self.profile_result = profile_result
        self.should_fail = should_fail

    def profile_script(self, script_path, args=None, config=None):  # noqa: ANN001, ARG002
        if self.should_fail:
            msg = "profiling boom"
            raise RuntimeError(msg)
        return self.profile_result or ProfileResult(script_path=str(script_path), duration_ms=50.0)


class DummyHotspotDetector:
    def __init__(self, hotspots: list[HotSpot]) -> None:
        self.hotspots = hotspots

    def detect_hotspots(self, profile_result, threshold_pct=5.0):  # noqa: ANN001, ARG002
        return self.hotspots


class DummyTemplateOptimizer:
    def __init__(self, optimized_source: str) -> None:
        self.optimized_source = optimized_source

    def detect_applicable_templates(
        self, source_code: str, hotspot: HotSpot | None = None
    ) -> list[str]:
        return ["vectorize_loop"]

    def apply_template(self, source_code: str, template_name: str) -> str:  # noqa: ARG002
        return self.optimized_source


class DummyLlmOptimizer:
    def __init__(self, optimized_source: str) -> None:
        self.optimized_source = optimized_source

    def optimize_function(self, source_code: str, hotspot: HotSpot, config=None):  # noqa: ANN001, ARG002
        return OptimizationAttempt(
            attempt_id="llm_attempt",
            original_code=source_code,
            optimized_code=self.optimized_source,
            strategy="llm_generated",
            llm_model="mock-model",
        )


class DummyEquivalenceChecker:
    def __init__(self, equivalent: bool = True, reason: str = "") -> None:
        self.equivalent = equivalent
        self.reason = reason

    def check_equivalence(self, original, optimized, tolerance=1e-6):  # noqa: ANN001, ARG002
        return self.equivalent, self.reason


class DummyCoverageTracer:
    def __init__(self, coverage: BranchCoverage) -> None:
        self.coverage = coverage
        self.uncovered_called = False

    def trace_branches(self, script_path, args=None):  # noqa: ANN001, ARG002
        return self.coverage

    def get_uncovered_branches(self, coverage: BranchCoverage) -> list[tuple[str, int]]:
        self.uncovered_called = True
        return [
            (item.branch_type, item.line_number)
            for item in coverage.branch_details
            if not item.taken
        ]


def test_profile_optimize_pipeline_template_strategy(tmp_path: Path) -> None:
    script = _write_script(tmp_path, "def target(x):\n    return x + 1\n")
    profiler_result = _profile_result(script)
    hotspot = _hotspot("target", script)
    orchestrator = DefaultOrchestrator(
        config_loader=DummyConfigLoader(),
        profiler=DummyProfiler(profile_result=profiler_result),
        hotspot_detector=DummyHotspotDetector([hotspot]),
        template_optimizer=DummyTemplateOptimizer("def target(x):\n    return x + 1\n"),
        equivalence_checker=DummyEquivalenceChecker(equivalent=True),
    )

    result = orchestrator.run_profile_optimize_pipeline(
        script_path=str(script),
        function_name="target",
        strategy="template",
    )

    assert result.best_attempt is not None
    assert result.best_attempt.strategy == "template"
    assert result.best_attempt.syntax_valid is True
    assert result.best_attempt.passed_equivalence is True


def test_profile_optimize_pipeline_llm_strategy(tmp_path: Path) -> None:
    script = _write_script(tmp_path, "def target(x):\n    return x + 1\n")
    profiler_result = _profile_result(script)
    hotspot = _hotspot("target", script)
    orchestrator = DefaultOrchestrator(
        config_loader=DummyConfigLoader(),
        profiler=DummyProfiler(profile_result=profiler_result),
        hotspot_detector=DummyHotspotDetector([hotspot]),
        llm_optimizer=DummyLlmOptimizer("def target(x):\n    return x + 1\n"),
        equivalence_checker=DummyEquivalenceChecker(equivalent=True),
    )

    result = orchestrator.run_profile_optimize_pipeline(
        script_path=str(script),
        function_name="target",
        strategy="llm",
    )

    assert result.best_attempt is not None
    assert result.best_attempt.strategy == "llm_generated"
    assert result.best_attempt.llm_model == "mock-model"


def test_coverage_replay_pipeline(tmp_path: Path) -> None:
    script = _write_script(tmp_path, "def main():\n    return 1\n")
    coverage = BranchCoverage(
        total_branches=2,
        covered_branches=1,
        coverage_percent=50.0,
        uncovered_lines=[2],
        branch_details=[
            BranchInfo(line_number=1, branch_type="if", condition="", taken=True),
            BranchInfo(line_number=2, branch_type="else", condition="", taken=False),
        ],
        script_path=str(script),
        duration_ms=1.0,
    )
    tracer = DummyCoverageTracer(coverage)
    orchestrator = DefaultOrchestrator(config_loader=DummyConfigLoader(), coverage_tracer=tracer)

    result = orchestrator.run_coverage_replay_pipeline(str(script))

    assert result == coverage
    assert tracer.uncovered_called is True


def test_pipeline_state_tracking() -> None:
    state = PipelineState(pipeline_type="profile_optimize")
    state.advance("load_config")
    state.complete_step(12.3)
    state.advance("profile")
    state.fail_step("boom")

    assert isinstance(state.steps[0], PipelineStep)
    assert state.steps[0].status == "completed"
    assert state.steps[0].duration_ms == 12.3
    assert state.steps[1].status == "failed"
    assert state.steps[1].error == "boom"


def test_error_handling_when_profiling_fails(tmp_path: Path) -> None:
    script = _write_script(tmp_path, "def target(x):\n    return x\n")
    orchestrator = DefaultOrchestrator(
        config_loader=DummyConfigLoader(),
        profiler=DummyProfiler(should_fail=True),
        hotspot_detector=DummyHotspotDetector([]),
    )

    result = orchestrator.run_profile_optimize_pipeline(
        script_path=str(script),
        function_name="target",
    )

    assert result.best_attempt is None
    assert result.attempts
    assert "profiling boom" in (result.attempts[0].error_message or "")


def test_error_handling_when_equivalence_fails(tmp_path: Path) -> None:
    script = _write_script(tmp_path, "def target(x):\n    return x + 1\n")
    profiler_result = _profile_result(script)
    hotspot = _hotspot("target", script)
    orchestrator = DefaultOrchestrator(
        config_loader=DummyConfigLoader(),
        profiler=DummyProfiler(profile_result=profiler_result),
        hotspot_detector=DummyHotspotDetector([hotspot]),
        llm_optimizer=DummyLlmOptimizer("def target(x):\n    return x + 2\n"),
        equivalence_checker=DummyEquivalenceChecker(equivalent=False, reason="mismatch"),
    )

    result = orchestrator.run_profile_optimize_pipeline(
        script_path=str(script),
        function_name="target",
        strategy="llm",
    )

    assert result.best_attempt is None
    assert result.attempts[0].passed_equivalence is False
    assert result.attempts[0].error_message == "mismatch"


def test_when_function_not_found_in_hotspots(tmp_path: Path) -> None:
    script = _write_script(tmp_path, "def target(x):\n    return x\n")
    profiler_result = _profile_result(script)
    other_hotspot = _hotspot("other", script)
    orchestrator = DefaultOrchestrator(
        config_loader=DummyConfigLoader(),
        profiler=DummyProfiler(profile_result=profiler_result),
        hotspot_detector=DummyHotspotDetector([other_hotspot]),
    )

    result = orchestrator.run_profile_optimize_pipeline(
        script_path=str(script),
        function_name="target",
    )

    assert result.best_attempt is None
    assert "not found in detected hotspots" in (result.attempts[0].error_message or "")

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


class ConditionalEquivalenceChecker:
    def __init__(self, results: list[tuple[bool, str]]) -> None:
        self._results = list(results)
        self._idx = 0

    def check_equivalence(  # noqa: ANN001, ARG002
        self, original, optimized, tolerance=1e-6
    ):
        result = self._results[self._idx]
        self._idx += 1
        return result


class TrackingLlmOptimizer(DummyLlmOptimizer):
    def __init__(self) -> None:
        super().__init__("")
        self.called = False

    def optimize_function(self, source_code, hotspot, config=None):  # noqa: ANN001
        self.called = True
        return super().optimize_function(source_code, hotspot, config)


class FailingConfigLoader:
    def load_config(self, config_path=None):  # noqa: ANN001, ARG002
        msg = "should not be called when config is provided"
        raise RuntimeError(msg)


class TestAutoStrategy:
    def test_auto_falls_back_to_llm_when_template_fails(self, tmp_path: Path) -> None:
        script = _write_script(tmp_path, "def target(x):\n    return x + 1\n")
        profiler_result = _profile_result(script)
        hotspot = _hotspot("target", script)
        llm_opt = DummyLlmOptimizer("def target(x):\n    return x + 1\n")
        orchestrator = DefaultOrchestrator(
            config_loader=DummyConfigLoader(),
            profiler=DummyProfiler(profile_result=profiler_result),
            hotspot_detector=DummyHotspotDetector([hotspot]),
            template_optimizer=DummyTemplateOptimizer("def target(x):\n    return x + 2\n"),
            llm_optimizer=llm_opt,
            equivalence_checker=ConditionalEquivalenceChecker(
                [(False, "output mismatch"), (True, "")]
            ),
        )

        result = orchestrator.run_profile_optimize_pipeline(
            script_path=str(script),
            function_name="target",
            strategy="auto",
        )

        assert result.best_attempt is not None
        assert result.best_attempt.strategy == "llm_generated"
        assert len(result.attempts) == 2
        assert result.attempts[0].strategy == "template"
        assert result.attempts[0].passed_equivalence is False

    def test_auto_uses_template_when_template_succeeds(self, tmp_path: Path) -> None:
        script = _write_script(tmp_path, "def target(x):\n    return x + 1\n")
        profiler_result = _profile_result(script)
        hotspot = _hotspot("target", script)
        tracking_llm = TrackingLlmOptimizer()
        orchestrator = DefaultOrchestrator(
            config_loader=DummyConfigLoader(),
            profiler=DummyProfiler(profile_result=profiler_result),
            hotspot_detector=DummyHotspotDetector([hotspot]),
            template_optimizer=DummyTemplateOptimizer("def target(x):\n    return x + 1\n"),
            llm_optimizer=tracking_llm,
            equivalence_checker=ConditionalEquivalenceChecker([(True, "")]),
        )

        result = orchestrator.run_profile_optimize_pipeline(
            script_path=str(script),
            function_name="target",
            strategy="auto",
        )

        assert result.best_attempt is not None
        assert result.best_attempt.strategy == "template"
        assert len(result.attempts) == 1
        assert tracking_llm.called is False

    def test_coverage_pipeline_records_all_steps(self, tmp_path: Path) -> None:
        script = _write_script(tmp_path, "def main():\n    return 1\n")
        coverage = BranchCoverage(
            total_branches=1,
            covered_branches=1,
            coverage_percent=100.0,
            uncovered_lines=[],
            branch_details=[
                BranchInfo(line_number=1, branch_type="if", condition="", taken=True),
            ],
            script_path=str(script),
            duration_ms=1.0,
        )
        tracer = DummyCoverageTracer(coverage)
        orchestrator = DefaultOrchestrator(
            config_loader=DummyConfigLoader(), coverage_tracer=tracer
        )

        orchestrator.run_coverage_replay_pipeline(str(script))

        state = orchestrator.last_pipeline_state
        assert state is not None
        step_names = [s.name for s in state.steps]
        assert step_names == [
            "load_config",
            "trace_branches",
            "get_uncovered_branches",
        ]
        assert all(s.status == "completed" for s in state.steps)
        assert all(s.duration_ms > 0 for s in state.steps)

    def test_custom_config_used_by_pipeline(self, tmp_path: Path) -> None:
        script = _write_script(tmp_path, "def target(x):\n    return x + 1\n")
        profiler_result = _profile_result(script)
        hotspot = _hotspot("target", script)
        custom_cfg = ArwizConfig(equivalence_tolerance=0.01)
        orchestrator = DefaultOrchestrator(
            config_loader=FailingConfigLoader(),
            profiler=DummyProfiler(profile_result=profiler_result),
            hotspot_detector=DummyHotspotDetector([hotspot]),
            template_optimizer=DummyTemplateOptimizer("def target(x):\n    return x + 1\n"),
            equivalence_checker=DummyEquivalenceChecker(equivalent=True),
        )

        result = orchestrator.run_profile_optimize_pipeline(
            script_path=str(script),
            function_name="target",
            strategy="template",
            config=custom_cfg,
        )

        assert result.best_attempt is not None
        assert result.best_attempt.passed_equivalence is True

    def test_empty_hotspot_list_handled_gracefully(self, tmp_path: Path) -> None:
        script = _write_script(tmp_path, "def target(x):\n    return x\n")
        orchestrator = DefaultOrchestrator(
            config_loader=DummyConfigLoader(),
            profiler=DummyProfiler(),
            hotspot_detector=DummyHotspotDetector([]),
        )

        result = orchestrator.run_profile_optimize_pipeline(
            script_path=str(script),
            function_name="target",
        )

        assert result.best_attempt is None
        assert len(result.attempts) == 1
        assert "not found" in (result.attempts[0].error_message or "")
        state = orchestrator.last_pipeline_state
        assert state is not None
        step_names = [s.name for s in state.steps]
        assert "detect_hotspots" in step_names
        assert "find_target_hotspot" in step_names
        assert state.steps[-1].status == "failed"

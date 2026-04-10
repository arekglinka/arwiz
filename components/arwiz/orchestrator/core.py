from __future__ import annotations

import ast
import logging
from importlib import import_module
from inspect import Parameter, Signature, signature
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from ..config import DefaultConfigLoader
from ..coverage_tracer import DefaultCoverageTracer
from ..equivalence import DefaultEquivalenceChecker
from ..foundation import (
    ArwizConfig,
    BranchCoverage,
    HotSpot,
    OptimizationAttempt,
    OptimizationResult,
)
from ..hotspot import DefaultHotspotDetector
from ..llm_optimizer import DefaultLLMOptimizer
from ..process_manager import DefaultProcessManager
from ..profiler import DefaultProfiler
from ..template_optimizer import DefaultTemplateOptimizer
from .pipeline_state import PipelineState

# given polylith brick mapping metadata,
# when syncing brick coordinates, then "components/arwiz/orchestrator" = "arwiz/orchestrator"

logger = logging.getLogger(__name__)


class DefaultOrchestrator:
    _BACKEND_TEMPLATE_MAP: dict[str, str] = {
        "numba": "numba_jit",
        "cython": "cython_optimize",
        "numba_parallel": "numba_parallel",
        "jax": "jax_optimize",
        "cupy": "cupy_optimize",
        "numexpr": "numexpr_optimize",
        "pyo3": "pyo3_optimize",
        "cffi": "cffi_optimize",
    }

    def __init__(
        self,
        config_loader: DefaultConfigLoader | None = None,
        profiler: DefaultProfiler | None = None,
        hotspot_detector: DefaultHotspotDetector | None = None,
        template_optimizer: DefaultTemplateOptimizer | None = None,
        llm_optimizer: DefaultLLMOptimizer | None = None,
        equivalence_checker: DefaultEquivalenceChecker | None = None,
        coverage_tracer: DefaultCoverageTracer | None = None,
        process_manager: DefaultProcessManager | None = None,
        backend_selector: Any | None = None,
    ) -> None:
        self._process_manager = process_manager or DefaultProcessManager()
        self._config_loader = config_loader or DefaultConfigLoader()
        self._profiler = profiler or DefaultProfiler(process_manager=self._process_manager)
        self._hotspot_detector = hotspot_detector or DefaultHotspotDetector()
        self._template_optimizer = template_optimizer or DefaultTemplateOptimizer()
        self._llm_optimizer = llm_optimizer or DefaultLLMOptimizer()
        self._equivalence_checker = equivalence_checker or DefaultEquivalenceChecker()
        self._coverage_tracer = coverage_tracer or DefaultCoverageTracer()
        if backend_selector is None:
            selector_cls = import_module("arwiz.backend_selector").DefaultBackendSelector
            self._backend_selector = selector_cls()
        else:
            self._backend_selector = backend_selector
        self.last_pipeline_state: PipelineState | None = None

    def _make_error_attempt(
        self,
        original_code: str,
        strategy: str,
        error: str,
        template_name: str | None = None,
        backend: str | None = None,
    ) -> OptimizationAttempt:
        return OptimizationAttempt(
            attempt_id=f"opt_{uuid4().hex[:12]}",
            original_code=original_code,
            optimized_code="",
            strategy=strategy,
            template_name=template_name,
            backend=backend,
            error_message=error,
        )

    def run_profile_optimize_pipeline(
        self,
        script_path: str,
        function_name: str,
        strategy: str = "auto",
        config: ArwizConfig | None = None,
    ) -> OptimizationResult:
        state = PipelineState(pipeline_type="profile_optimize")
        self.last_pipeline_state = state

        try:
            cfg = self._run_step(
                state, "load_config", lambda: config or self._config_loader.load_config()
            )
            profile_result = self._run_step(
                state,
                "profile_script",
                lambda: self._profiler.profile_script(script_path, args=[], config=cfg),
            )
            hotspots = self._run_step(
                state,
                "detect_hotspots",
                lambda: self._hotspot_detector.detect_hotspots(profile_result),
            )
            target_hotspot = self._run_step(
                state,
                "find_target_hotspot",
                lambda: self._find_hotspot_by_name(hotspots, function_name),
            )
            original_source = self._run_step(
                state,
                "extract_function_source",
                lambda: self._extract_function_source(Path(script_path), function_name),
            )
        except Exception as exc:
            return OptimizationResult(
                function_name=function_name,
                file_path=script_path,
                attempts=[
                    self._make_error_attempt(
                        original_code="",
                        strategy=strategy,
                        error=f"Pipeline failed before optimization: {exc}",
                    )
                ],
                best_attempt=None,
                applied=False,
                total_time_saved_ms=0.0,
            )

        attempts: list[OptimizationAttempt] = []

        backend_ranking: list[tuple[str, float]] = []
        try:
            backend_ranking = self._backend_selector.rank_backends(original_source, target_hotspot)
        except Exception as exc:
            logger.warning("Backend ranking failed: %s", exc)
            backend_ranking = []
        state.backend_ranking = backend_ranking

        selected_strategy = strategy.lower().strip()
        allowed_strategies = {
            "auto",
            "template",
            "llm",
            *self._BACKEND_TEMPLATE_MAP.keys(),
        }
        if selected_strategy not in allowed_strategies:
            selected_strategy = "auto"

        if selected_strategy == "template":
            try:
                template_attempt = self._run_template_attempt(
                    state=state,
                    source=original_source,
                    hotspot=target_hotspot,
                    function_name=function_name,
                    tolerance=cfg.equivalence_tolerance,
                )
            except Exception as exc:
                template_attempt = self._make_error_attempt(
                    original_code=original_source,
                    strategy="template",
                    error=str(exc),
                )
            attempts.append(template_attempt)
            return self._build_result(function_name, script_path, attempts)

        if selected_strategy == "auto":
            try:
                selected_backends = self._run_step(
                    state,
                    "select_backends",
                    lambda: self._backend_selector.select_backends(original_source, target_hotspot),
                )
            except Exception as exc:
                logger.warning("Backend selection failed: %s", exc)
                selected_backends = []

            available_templates = self._run_step(
                state,
                "list_templates",
                self._template_optimizer.list_templates,
            )

            for backend_name in selected_backends:
                template_name = self._BACKEND_TEMPLATE_MAP.get(backend_name)
                if not template_name:
                    continue

                if template_name not in available_templates:
                    continue

                try:
                    backend_attempt = self._run_backend_template_attempt(
                        state=state,
                        source=original_source,
                        function_name=function_name,
                        tolerance=cfg.equivalence_tolerance,
                        backend_name=backend_name,
                        template_name=template_name,
                    )
                except Exception as exc:
                    backend_attempt = self._make_error_attempt(
                        original_code=original_source,
                        strategy="template",
                        error=str(exc),
                        template_name=template_name,
                        backend=backend_name,
                    )
                attempts.append(backend_attempt)
                if backend_attempt.syntax_valid and backend_attempt.passed_equivalence:
                    return self._build_result(function_name, script_path, attempts)

        if selected_strategy in self._BACKEND_TEMPLATE_MAP:
            backend_name = selected_strategy
            template_name = self._BACKEND_TEMPLATE_MAP[backend_name]
            available_templates = self._run_step(
                state,
                "list_templates",
                self._template_optimizer.list_templates,
            )
            if template_name in available_templates:
                try:
                    backend_attempt = self._run_backend_template_attempt(
                        state=state,
                        source=original_source,
                        function_name=function_name,
                        tolerance=cfg.equivalence_tolerance,
                        backend_name=backend_name,
                        template_name=template_name,
                    )
                except Exception as exc:
                    backend_attempt = self._make_error_attempt(
                        original_code=original_source,
                        strategy="template",
                        error=str(exc),
                        template_name=template_name,
                        backend=backend_name,
                    )
            else:
                backend_attempt = OptimizationAttempt(
                    attempt_id=f"opt_{uuid4().hex[:12]}",
                    original_code=original_source,
                    optimized_code=original_source,
                    strategy="template",
                    template_name=template_name,
                    backend=backend_name,
                    syntax_valid=True,
                    passed_equivalence=False,
                    error_message=f"Template '{template_name}' not available",
                )
            attempts.append(backend_attempt)
            if backend_attempt.syntax_valid and backend_attempt.passed_equivalence:
                return self._build_result(function_name, script_path, attempts)

        try:
            llm_attempt = self._run_llm_attempt(
                state=state,
                source=original_source,
                hotspot=target_hotspot,
                function_name=function_name,
                config=cfg,
                tolerance=cfg.equivalence_tolerance,
            )
        except Exception as exc:
            llm_attempt = self._make_error_attempt(
                original_code=original_source,
                strategy="llm",
                error=str(exc),
            )
        attempts.append(llm_attempt)
        return self._build_result(function_name, script_path, attempts)

    def run_coverage_replay_pipeline(
        self,
        script_path: str,
        config: ArwizConfig | None = None,
    ) -> BranchCoverage:
        state = PipelineState(pipeline_type="coverage_replay")
        self.last_pipeline_state = state

        self._run_step(state, "load_config", lambda: config or self._config_loader.load_config())
        coverage = self._run_step(
            state,
            "trace_branches",
            lambda: self._coverage_tracer.trace_branches(script_path, args=[]),
        )
        self._run_step(
            state,
            "get_uncovered_branches",
            lambda: self._coverage_tracer.get_uncovered_branches(coverage),
        )
        return coverage

    def _run_template_attempt(
        self,
        state: PipelineState,
        source: str,
        hotspot: HotSpot,
        function_name: str,
        tolerance: float,
    ) -> OptimizationAttempt:
        detected = self._run_step(
            state,
            "detect_templates",
            lambda: self._template_optimizer.detect_applicable_templates(source, hotspot),
        )
        if not detected:
            return OptimizationAttempt(
                attempt_id=f"opt_{uuid4().hex[:12]}",
                original_code=source,
                optimized_code=source,
                strategy="template",
                syntax_valid=True,
                passed_equivalence=False,
                error_message="No applicable template found",
            )

        template_name = detected[0]
        optimized_source = self._run_step(
            state,
            "apply_template",
            lambda: self._template_optimizer.apply_template(source, template_name),
        )
        return self._finalize_attempt(
            state=state,
            attempt=OptimizationAttempt(
                attempt_id=f"opt_{uuid4().hex[:12]}",
                original_code=source,
                optimized_code=optimized_source,
                strategy="template",
                template_name=template_name,
            ),
            function_name=function_name,
            tolerance=tolerance,
        )

    def _run_llm_attempt(
        self,
        state: PipelineState,
        source: str,
        hotspot: HotSpot,
        function_name: str,
        config: ArwizConfig,
        tolerance: float,
    ) -> OptimizationAttempt:
        attempt = self._run_step(
            state,
            "optimize_with_llm",
            lambda: self._llm_optimizer.optimize_function(source, hotspot, config.llm_config),
        )
        return self._finalize_attempt(
            state=state,
            attempt=attempt,
            function_name=function_name,
            tolerance=tolerance,
        )

    def _run_backend_template_attempt(
        self,
        state: PipelineState,
        source: str,
        function_name: str,
        tolerance: float,
        backend_name: str,
        template_name: str,
    ) -> OptimizationAttempt:
        optimized_source = self._run_step(
            state,
            "apply_template",
            lambda: self._template_optimizer.apply_template(source, template_name),
        )
        return self._finalize_attempt(
            state=state,
            attempt=OptimizationAttempt(
                attempt_id=f"opt_{uuid4().hex[:12]}",
                original_code=source,
                optimized_code=optimized_source,
                strategy="template",
                template_name=template_name,
                backend=backend_name,
            ),
            function_name=function_name,
            tolerance=tolerance,
        )

    def _finalize_attempt(
        self,
        state: PipelineState,
        attempt: OptimizationAttempt,
        function_name: str,
        tolerance: float,
    ) -> OptimizationAttempt:
        syntax_valid, syntax_error = self._run_step(
            state,
            "validate_syntax",
            lambda: self._validate_syntax(attempt.optimized_code),
        )
        attempt.syntax_valid = syntax_valid
        if not syntax_valid:
            attempt.error_message = syntax_error
            attempt.passed_equivalence = False
            return attempt

        equivalent, reason = self._run_step(
            state,
            "check_equivalence",
            lambda: self._check_equivalence(
                original_code=attempt.original_code,
                optimized_code=attempt.optimized_code,
                function_name=function_name,
                tolerance=tolerance,
            ),
        )
        attempt.passed_equivalence = equivalent
        if not equivalent:
            attempt.error_message = reason
        return attempt

    def _build_result(
        self,
        function_name: str,
        file_path: str,
        attempts: list[OptimizationAttempt],
    ) -> OptimizationResult:
        best_attempt = next((att for att in attempts if att.passed_equivalence), None)
        return OptimizationResult(
            function_name=function_name,
            file_path=file_path,
            attempts=attempts,
            best_attempt=best_attempt,
            applied=best_attempt is not None,
            total_time_saved_ms=0.0,
        )

    def _find_hotspot_by_name(self, hotspots: list[HotSpot], function_name: str) -> HotSpot:
        for hotspot in hotspots:
            if hotspot.function_name == function_name:
                return hotspot
        msg = f"Function '{function_name}' not found in detected hotspots"
        raise ValueError(msg)

    def _extract_function_source(self, script_path: Path, function_name: str) -> str:
        source = script_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in tree.body:
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == function_name
            ):
                segment = ast.get_source_segment(source, node)
                if segment:
                    return segment
                lines = source.splitlines()
                return "\n".join(lines[node.lineno - 1 : node.end_lineno])

        msg = f"Function '{function_name}' not found in source file"
        raise ValueError(msg)

    def _validate_syntax(self, code: str) -> tuple[bool, str]:
        try:
            compile(code, "<optimized>", "exec")
        except SyntaxError as exc:
            return False, str(exc)
        return True, ""

    def _check_equivalence(
        self,
        original_code: str,
        optimized_code: str,
        function_name: str,
        tolerance: float,
    ) -> tuple[bool, str]:
        original_fn = self._compile_function(original_code, function_name)
        optimized_fn = self._compile_function(optimized_code, function_name)
        samples = self._generate_sample_inputs(signature(original_fn))
        if not samples:
            samples = [((), {})]

        for args, kwargs in samples:
            try:
                original_output = original_fn(*args, **kwargs)
                optimized_output = optimized_fn(*args, **kwargs)
            except Exception as exc:
                return False, f"Execution failed on sample input: {exc}"

            equivalent, reason = self._equivalence_checker.check_equivalence(
                original_output,
                optimized_output,
                tolerance=tolerance,
            )
            if not equivalent:
                return False, reason
        return True, ""

    def _compile_function(self, source: str, function_name: str):
        namespace: dict[str, object] = {}
        exec(source, namespace)  # noqa: S102
        fn = namespace.get(function_name)
        if not callable(fn):
            msg = f"Function '{function_name}' missing from generated source"
            raise ValueError(msg)
        return fn

    def _generate_sample_inputs(self, sig: Signature) -> list[tuple[tuple, dict]]:
        required_positional = 0
        required_keyword_only: list[str] = []
        has_var_positional = False

        for param in sig.parameters.values():
            if param.kind is Parameter.VAR_POSITIONAL:
                has_var_positional = True
                continue
            if param.kind is Parameter.VAR_KEYWORD:
                continue
            if param.kind is Parameter.KEYWORD_ONLY and param.default is Parameter.empty:
                required_keyword_only.append(param.name)
                continue
            if (
                param.kind in {Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD}
                and param.default is Parameter.empty
            ):
                required_positional += 1

        kwargs = dict.fromkeys(required_keyword_only, 1)
        positional = tuple(1 for _ in range(required_positional))
        samples: list[tuple[tuple, dict]] = [(positional, kwargs)]

        if has_var_positional:
            samples.append(((*positional, 2, 3), kwargs.copy()))
        return samples

    def _run_step(self, state: PipelineState, name: str, action):
        state.advance(name)
        start = perf_counter()
        try:
            result = action()
        except Exception as exc:
            elapsed_ms = (perf_counter() - start) * 1000
            state.fail_step(str(exc))
            state.steps[state.current_step].duration_ms = elapsed_ms
            raise

        elapsed_ms = (perf_counter() - start) * 1000
        state.complete_step(elapsed_ms)
        return result

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest


def _foundation() -> Any:
    return import_module("arwiz.foundation")


def _orchestrator_cls() -> Any:
    return import_module("arwiz.orchestrator").DefaultOrchestrator


def _backend_selector_cls() -> Any:
    return import_module("arwiz.backend_selector").DefaultBackendSelector


def _llm_optimizer_cls() -> Any:
    return import_module("arwiz.llm_optimizer").DefaultLLMOptimizer


def _write_script(tmp_path: Path, source: str) -> Path:
    script = tmp_path / "target.py"
    script.write_text(source, encoding="utf-8")
    return script


def _hotspot(function_name: str, script_path: Path) -> Any:
    hot_spot = _foundation().HotSpot
    return hot_spot(
        function_name=function_name,
        file_path=str(script_path),
        line_range=(1, 20),
        cumulative_time_ms=100.0,
        self_time_ms=95.0,
        call_count=30,
    )


class DummyConfigLoader:
    def load_config(self, _config_path=None):  # noqa: ANN001
        return _foundation().ArwizConfig()


class DummyProfiler:
    def profile_script(self, script_path, args=None, config=None):  # noqa: ANN001
        duration_ms = 10.0 + (0.0 * len(args or []))
        if config is not None:
            duration_ms += 0.0
        return _foundation().ProfileResult(script_path=str(script_path), duration_ms=duration_ms)


class DummyHotspotDetector:
    def __init__(self, hotspots: list[Any]) -> None:
        self._hotspots = hotspots

    def detect_hotspots(self, _profile_result, _threshold_pct=5.0):  # noqa: ANN001
        return list(self._hotspots)


class StaticBackendSelector:
    def __init__(
        self,
        selected_backends: list[str] | None = None,
        ranking: list[tuple[str, float]] | None = None,
        fail_on_select: bool = False,
    ) -> None:
        self.selected_backends = selected_backends or []
        self.ranking = ranking or []
        self.fail_on_select = fail_on_select
        self.select_called = False

    def select_backends(self, _source_code: str, _hotspot: Any = None) -> list[str]:
        self.select_called = True
        if self.fail_on_select:
            msg = "select_backends should not be called"
            raise AssertionError(msg)
        return list(self.selected_backends)

    def rank_backends(self, _source_code: str, _hotspot: Any = None) -> list[tuple[str, float]]:
        return list(self.ranking)

    def get_manifest(self) -> dict[str, Any]:
        return {}

    def is_backend_available(self, _name: str) -> bool:
        return True


class MappingTemplateOptimizer:
    def __init__(
        self,
        templates: list[str],
        outputs: dict[str, str] | None = None,
        errors: dict[str, str] | None = None,
        detected: list[str] | None = None,
    ) -> None:
        self._templates = list(templates)
        self._outputs = outputs or {}
        self._errors = errors or {}
        self._detected = ["vectorize_loop"] if detected is None else list(detected)
        self.applied_templates: list[str] = []

    def list_templates(self) -> list[str]:
        return list(self._templates)

    def detect_applicable_templates(self, _source_code: str, _hotspot: Any = None) -> list[str]:
        return list(self._detected)

    def apply_template(self, source_code: str, template_name: str) -> str:
        self.applied_templates.append(template_name)
        if template_name in self._errors:
            raise RuntimeError(self._errors[template_name])
        return self._outputs.get(template_name, source_code)


class TrackingLlmOptimizer:
    def __init__(self, optimized_source: str) -> None:
        self.optimized_source = optimized_source
        self.called = False

    def optimize_function(self, source_code: str, _hotspot: Any, _config=None):  # noqa: ANN001
        self.called = True
        return _foundation().OptimizationAttempt(
            attempt_id=f"llm_{uuid4().hex[:8]}",
            original_code=source_code,
            optimized_code=self.optimized_source,
            strategy="llm_generated",
            llm_model="mock-model",
            syntax_valid=True,
        )


class _MockProvider:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def generate(self, prompt: str, _model: str, **kwargs: object) -> str:  # noqa: ARG002
        self.prompts.append(prompt)
        return "```python\ndef target(x):\n    return x + 1\n```"


def _build_orchestrator(
    script: Path,
    *,
    function_name: str = "target",
    template_optimizer: Any | None = None,
    llm_optimizer: Any | None = None,
    backend_selector: Any | None = None,
) -> Any:
    return _orchestrator_cls()(
        config_loader=DummyConfigLoader(),
        profiler=DummyProfiler(),
        hotspot_detector=DummyHotspotDetector([_hotspot(function_name, script)]),
        template_optimizer=template_optimizer,
        llm_optimizer=llm_optimizer,
        backend_selector=backend_selector,
    )


def _set_equivalence_sequence(orchestrator: Any, outcomes: list[tuple[bool, str]]) -> None:
    sequence = list(outcomes)

    def _check_equivalence(*args: object, **kwargs: object) -> tuple[bool, str]:  # noqa: ARG001
        if sequence:
            return sequence.pop(0)
        return True, ""

    orchestrator._check_equivalence = _check_equivalence  # noqa: SLF001


@pytest.mark.integration
class TestE2EBackends:
    def test_auto_strategy_detects_loops_to_numba_or_vectorize(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        source = (
            "def target(n):\n"
            "    total = 0\n"
            "    for i in range(n):\n"
            "        for j in range(n):\n"
            "            total += i * j\n"
            "    return total\n"
        )
        script = _write_script(tmp_path, source)
        selector = _backend_selector_cls()()
        monkeypatch.setattr(selector, "is_backend_available", lambda _name: True)

        template_optimizer = MappingTemplateOptimizer(
            templates=["cython_optimize", "numba_jit"],
            outputs={
                "cython_optimize": "def target(n):\n    return n\n",
                "numba_jit": "def target(n):\n    return n\n",
            },
        )
        orchestrator = _build_orchestrator(
            script,
            template_optimizer=template_optimizer,
            llm_optimizer=TrackingLlmOptimizer("def target(n):\n    return n\n"),
            backend_selector=selector,
        )
        _set_equivalence_sequence(orchestrator, [(True, "")])

        result = orchestrator.run_profile_optimize_pipeline(
            script_path=str(script), function_name="target", strategy="auto"
        )

        assert result.best_attempt is not None
        assert result.best_attempt.backend in {"numba", "cython"}
        assert result.best_attempt.template_name in {"numba_jit", "cython_optimize"}

    def test_auto_strategy_detects_string_ops_to_pyo3(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        source = (
            "def target(text):\n"
            "    chunks = text.strip().split(',')\n"
            "    return '_'.join(chunks).lower()\n"
        )
        script = _write_script(tmp_path, source)
        selector = _backend_selector_cls()()
        monkeypatch.setattr(selector, "is_backend_available", lambda _name: True)

        template_optimizer = MappingTemplateOptimizer(
            templates=["pyo3_optimize"],
            outputs={"pyo3_optimize": "def target(text):\n    return text\n"},
        )
        orchestrator = _build_orchestrator(
            script,
            template_optimizer=template_optimizer,
            llm_optimizer=TrackingLlmOptimizer("def target(text):\n    return text\n"),
            backend_selector=selector,
        )
        _set_equivalence_sequence(orchestrator, [(True, "")])

        result = orchestrator.run_profile_optimize_pipeline(
            script_path=str(script), function_name="target", strategy="auto"
        )

        assert result.best_attempt is not None
        assert result.best_attempt.backend == "pyo3"
        assert result.best_attempt.template_name == "pyo3_optimize"

    def test_auto_strategy_detects_numpy_calls_to_jax_or_cupy(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        source = (
            "import numpy as np\n\ndef target(x):\n    arr = np.array(x)\n    return np.sum(arr)\n"
        )
        script = _write_script(tmp_path, source)
        selector = _backend_selector_cls()()
        monkeypatch.setattr(selector, "is_backend_available", lambda _name: True)

        template_optimizer = MappingTemplateOptimizer(
            templates=["jax_optimize", "cupy_optimize"],
            outputs={
                "jax_optimize": "def target(x):\n    return x\n",
                "cupy_optimize": "def target(x):\n    return x\n",
            },
        )
        orchestrator = _build_orchestrator(
            script,
            template_optimizer=template_optimizer,
            llm_optimizer=TrackingLlmOptimizer("def target(x):\n    return x\n"),
            backend_selector=selector,
        )
        _set_equivalence_sequence(orchestrator, [(True, "")])

        result = orchestrator.run_profile_optimize_pipeline(
            script_path=str(script), function_name="target", strategy="auto"
        )

        assert result.best_attempt is not None
        assert result.best_attempt.backend in {"jax", "cupy"}
        assert result.best_attempt.template_name in {"jax_optimize", "cupy_optimize"}

    def test_auto_strategy_ambiguous_code_uses_manifest_context(self, tmp_path: Path) -> None:
        source = "def target(x):\n    y = x + 1\n    return y\n"
        script = _write_script(tmp_path, source)
        selector = _backend_selector_cls()()

        llm_optimizer = _llm_optimizer_cls()()
        provider = _MockProvider()
        llm_optimizer.provider = provider
        llm_optimizer.backend_manifest = import_module(
            "arwiz.backend_selector.manifest"
        ).BackendManifest()

        template_optimizer = MappingTemplateOptimizer(templates=["numba_jit"])
        orchestrator = _build_orchestrator(
            script,
            template_optimizer=template_optimizer,
            llm_optimizer=llm_optimizer,
            backend_selector=selector,
        )
        _set_equivalence_sequence(orchestrator, [(True, "")])

        result = orchestrator.run_profile_optimize_pipeline(
            script_path=str(script), function_name="target", strategy="auto"
        )

        assert result.best_attempt is not None
        assert result.best_attempt.strategy == "llm_generated"
        assert provider.prompts
        assert "Backend selection context" in provider.prompts[-1]

    def test_specific_strategy_cython_bypasses_selector(self, tmp_path: Path) -> None:
        source = "def target(x):\n    return x + 1\n"
        script = _write_script(tmp_path, source)
        selector = StaticBackendSelector(fail_on_select=True)
        template_optimizer = MappingTemplateOptimizer(
            templates=["cython_optimize"],
            outputs={"cython_optimize": "def target(x):\n    return x + 2\n"},
        )
        llm_optimizer = TrackingLlmOptimizer("def target(x):\n    return x + 3\n")
        orchestrator = _build_orchestrator(
            script,
            template_optimizer=template_optimizer,
            llm_optimizer=llm_optimizer,
            backend_selector=selector,
        )
        _set_equivalence_sequence(orchestrator, [(True, "")])

        result = orchestrator.run_profile_optimize_pipeline(
            script_path=str(script), function_name="target", strategy="cython"
        )

        assert result.best_attempt is not None
        assert result.best_attempt.backend == "cython"
        assert result.best_attempt.template_name == "cython_optimize"
        assert selector.select_called is False
        assert llm_optimizer.called is False

    def test_specific_strategy_jax_bypasses_selector(self, tmp_path: Path) -> None:
        source = "def target(x):\n    return x\n"
        script = _write_script(tmp_path, source)
        selector = StaticBackendSelector(fail_on_select=True)
        template_optimizer = MappingTemplateOptimizer(
            templates=["jax_optimize"],
            outputs={"jax_optimize": "def target(x):\n    return x\n"},
        )
        llm_optimizer = TrackingLlmOptimizer("def target(x):\n    return x\n")
        orchestrator = _build_orchestrator(
            script,
            template_optimizer=template_optimizer,
            llm_optimizer=llm_optimizer,
            backend_selector=selector,
        )
        _set_equivalence_sequence(orchestrator, [(True, "")])

        result = orchestrator.run_profile_optimize_pipeline(
            script_path=str(script), function_name="target", strategy="jax"
        )

        assert result.best_attempt is not None
        assert result.best_attempt.backend == "jax"
        assert result.best_attempt.template_name == "jax_optimize"
        assert selector.select_called is False
        assert llm_optimizer.called is False

    def test_specific_strategy_pyo3_bypasses_selector(self, tmp_path: Path) -> None:
        source = "def target(text):\n    return text.upper()\n"
        script = _write_script(tmp_path, source)
        selector = StaticBackendSelector(fail_on_select=True)
        template_optimizer = MappingTemplateOptimizer(
            templates=["pyo3_optimize"],
            outputs={"pyo3_optimize": "def target(text):\n    return text\n"},
        )
        llm_optimizer = TrackingLlmOptimizer("def target(text):\n    return text\n")
        orchestrator = _build_orchestrator(
            script,
            template_optimizer=template_optimizer,
            llm_optimizer=llm_optimizer,
            backend_selector=selector,
        )
        _set_equivalence_sequence(orchestrator, [(True, "")])

        result = orchestrator.run_profile_optimize_pipeline(
            script_path=str(script), function_name="target", strategy="pyo3"
        )

        assert result.best_attempt is not None
        assert result.best_attempt.backend == "pyo3"
        assert result.best_attempt.template_name == "pyo3_optimize"
        assert selector.select_called is False
        assert llm_optimizer.called is False

    def test_fallback_template_failure_tries_next_backend(self, tmp_path: Path) -> None:
        source = "def target(x):\n    return x + 1\n"
        script = _write_script(tmp_path, source)
        selector = StaticBackendSelector(selected_backends=["cython", "numba"])
        template_optimizer = MappingTemplateOptimizer(
            templates=["cython_optimize", "numba_jit"],
            outputs={"numba_jit": "def target(x):\n    return x + 2\n"},
            errors={"cython_optimize": "cython transform failed"},
        )
        llm_optimizer = TrackingLlmOptimizer("def target(x):\n    return x + 3\n")
        orchestrator = _build_orchestrator(
            script,
            template_optimizer=template_optimizer,
            llm_optimizer=llm_optimizer,
            backend_selector=selector,
        )
        _set_equivalence_sequence(orchestrator, [(True, "")])

        result = orchestrator.run_profile_optimize_pipeline(
            script_path=str(script), function_name="target", strategy="auto"
        )

        assert len(result.attempts) == 2
        assert result.attempts[0].backend == "cython"
        assert result.attempts[0].error_message == "cython transform failed"
        assert result.attempts[1].backend == "numba"
        assert result.best_attempt is not None
        assert result.best_attempt.backend == "numba"
        assert llm_optimizer.called is False

    def test_fallback_all_templates_fail_falls_back_to_llm(self, tmp_path: Path) -> None:
        source = "def target(x):\n    return x + 1\n"
        script = _write_script(tmp_path, source)
        selector = StaticBackendSelector(selected_backends=["cython", "numba"])
        template_optimizer = MappingTemplateOptimizer(
            templates=["cython_optimize", "numba_jit"],
            outputs={
                "cython_optimize": "def target(x):\n    return x + 2\n",
                "numba_jit": "def target(x):\n    return x + 3\n",
            },
        )

        llm_optimizer = _llm_optimizer_cls()()
        llm_optimizer.provider = _MockProvider()

        orchestrator = _build_orchestrator(
            script,
            template_optimizer=template_optimizer,
            llm_optimizer=llm_optimizer,
            backend_selector=selector,
        )
        _set_equivalence_sequence(
            orchestrator, [(False, "cython mismatch"), (False, "numba mismatch"), (True, "")]
        )

        result = orchestrator.run_profile_optimize_pipeline(
            script_path=str(script), function_name="target", strategy="auto"
        )

        assert len(result.attempts) == 3
        assert result.attempts[0].backend == "cython"
        assert result.attempts[0].passed_equivalence is False
        assert result.attempts[1].backend == "numba"
        assert result.attempts[1].passed_equivalence is False
        assert result.best_attempt is not None
        assert result.best_attempt.strategy == "llm_generated"

    def test_already_optimized_code_returns_no_optimization(self, tmp_path: Path) -> None:
        source = "@njit\ndef target(x):\n    return x + 1\n"
        script = _write_script(tmp_path, source)
        selector = StaticBackendSelector(selected_backends=["numba"])
        template_optimizer = MappingTemplateOptimizer(
            templates=["numba_jit"],
            outputs={"numba_jit": source},
        )
        orchestrator = _build_orchestrator(
            script,
            template_optimizer=template_optimizer,
            llm_optimizer=TrackingLlmOptimizer(source),
            backend_selector=selector,
        )
        _set_equivalence_sequence(orchestrator, [(True, "")])

        result = orchestrator.run_profile_optimize_pipeline(
            script_path=str(script), function_name="target", strategy="auto"
        )

        assert result.best_attempt is not None
        assert result.best_attempt.backend == "numba"
        assert result.best_attempt.passed_equivalence is True
        assert "return x + 1" in result.best_attempt.optimized_code

    def test_empty_function_returns_gracefully(self, tmp_path: Path) -> None:
        source = "def target():\n    pass\n"
        script = _write_script(tmp_path, source)
        template_optimizer = MappingTemplateOptimizer(templates=["vectorize_loop"], detected=[])
        orchestrator = _build_orchestrator(
            script,
            template_optimizer=template_optimizer,
            llm_optimizer=TrackingLlmOptimizer(source),
            backend_selector=StaticBackendSelector(),
        )

        result = orchestrator.run_profile_optimize_pipeline(
            script_path=str(script), function_name="target", strategy="template"
        )

        assert result.best_attempt is None
        assert result.applied is False
        assert len(result.attempts) == 1
        assert result.attempts[0].error_message == "No applicable template found"

    def test_no_applicable_backend_returns_original(self, tmp_path: Path) -> None:
        source = "def target(x):\n    return x + 1\n"
        script = _write_script(tmp_path, source)
        selector = StaticBackendSelector(selected_backends=[])

        class PassThroughLlm:
            def optimize_function(self, source_code: str, _hotspot: Any, _config=None):  # noqa: ANN001
                return _foundation().OptimizationAttempt(
                    attempt_id=f"llm_{uuid4().hex[:8]}",
                    original_code=source_code,
                    optimized_code=source_code,
                    strategy="llm_generated",
                    llm_model="mock",
                    syntax_valid=True,
                )

        orchestrator = _build_orchestrator(
            script,
            template_optimizer=MappingTemplateOptimizer(templates=["numba_jit"]),
            llm_optimizer=PassThroughLlm(),
            backend_selector=selector,
        )

        result = orchestrator.run_profile_optimize_pipeline(
            script_path=str(script), function_name="target", strategy="auto"
        )

        assert result.best_attempt is not None
        assert result.best_attempt.strategy == "llm_generated"
        assert result.best_attempt.optimized_code == result.best_attempt.original_code

    def test_all_attempts_have_backend_field_populated(self, tmp_path: Path) -> None:
        source = "def target(x):\n    return x + 1\n"
        script = _write_script(tmp_path, source)
        selector = StaticBackendSelector(selected_backends=["cython", "numba", "jax"])
        template_optimizer = MappingTemplateOptimizer(
            templates=["cython_optimize", "numba_jit", "jax_optimize"],
            outputs={
                "cython_optimize": "def target(x):\n    return x + 2\n",
                "numba_jit": "def target(x):\n    return x + 3\n",
                "jax_optimize": "def target(x):\n    return x + 4\n",
            },
        )
        llm_optimizer = TrackingLlmOptimizer("def target(x):\n    return x + 5\n")
        orchestrator = _build_orchestrator(
            script,
            template_optimizer=template_optimizer,
            llm_optimizer=llm_optimizer,
            backend_selector=selector,
        )
        _set_equivalence_sequence(orchestrator, [(False, "fail-1"), (False, "fail-2"), (True, "")])

        result = orchestrator.run_profile_optimize_pipeline(
            script_path=str(script), function_name="target", strategy="auto"
        )

        assert len(result.attempts) == 3
        assert all(attempt.backend for attempt in result.attempts)
        assert result.best_attempt is not None
        assert result.best_attempt.backend == "jax"
        assert llm_optimizer.called is False

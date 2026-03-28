from importlib import import_module
from typing import Any


def _optimizer_cls() -> Any:
    return import_module("arwiz.llm_optimizer.core").DefaultLLMOptimizer


def _foundation() -> Any:
    return import_module("arwiz.foundation")


def _prompts_module() -> Any:
    return import_module("arwiz.llm_optimizer.prompts")


def _hotspot() -> Any:
    hot_spot = _foundation().HotSpot
    return hot_spot(
        function_name="compute_sum",
        file_path="/tmp/simple_loop.py",
        line_range=(10, 20),
        cumulative_time_ms=321.0,
        self_time_ms=300.0,
        call_count=100,
        potential_speedup=2.0,
    )


def _backend_info_cls() -> Any:
    return _foundation().BackendInfo


def _llm_config() -> Any:
    llm_config = _foundation().LLMConfig
    return llm_config(provider="openai", model="gpt-4o", api_key_env_var="OPENAI_API_KEY")


class _MockProvider:
    def generate(self, _prompt: str, _model: str, **kwargs: object) -> str:  # noqa: ARG002
        return "```python\ndef optimized(x):\n    return x * 2\n```"


def test_build_manifest_context_formats_all_available_backends() -> None:
    prompts = _prompts_module()
    backend_info = _backend_info_cls()
    manifest = {
        "numba": backend_info(
            name="numba",
            tier=1,
            strengths=["JIT compilation", "nopython mode"],
            limitations=["limited strings"],
            ast_patterns=["for_loop"],
            best_for=["numeric loops"],
            performance_range=(10.0, 200.0),
            install_hint="pip install numba",
            is_available=True,
        ),
        "cython": backend_info(
            name="cython",
            tier=1,
            strengths=["typed memoryviews"],
            limitations=["build step"],
            ast_patterns=["nested_loops"],
            best_for=["complex loops"],
            performance_range=(10.0, 100.0),
            install_hint="pip install cython",
            is_available=True,
        ),
        "jax": backend_info(
            name="jax",
            tier=2,
            strengths=["XLA JIT"],
            limitations=["trace limitations"],
            ast_patterns=["array_operations"],
            best_for=["large arrays"],
            performance_range=(5.0, 100.0),
            install_hint="pip install jax",
            is_available=True,
        ),
    }

    rendered = prompts.build_manifest_context(manifest)

    assert "numba" in rendered
    assert "cython" in rendered
    assert "jax" in rendered
    assert "JIT compilation" in rendered
    assert "typed memoryviews" in rendered
    assert "Performance range" in rendered


def test_build_manifest_context_filters_unavailable_when_flag_set() -> None:
    prompts = _prompts_module()
    backend_info = _backend_info_cls()
    manifest = {
        "numba": backend_info(
            name="numba",
            tier=1,
            strengths=["JIT"],
            limitations=["objs"],
            ast_patterns=[],
            best_for=["loops"],
            performance_range=(10.0, 200.0),
            install_hint="pip install numba",
            is_available=True,
        ),
        "taichi": backend_info(
            name="taichi",
            tier=3,
            strengths=["GPU"],
            limitations=["py version"],
            ast_patterns=[],
            best_for=["simulation"],
            performance_range=(10.0, 500.0),
            install_hint="pip install taichi",
            is_available=False,
            availability_reason="unsupported",
        ),
    }

    rendered = prompts.build_manifest_context(manifest, available_only=True)

    assert "numba" in rendered
    assert "taichi" not in rendered


def test_build_manifest_context_includes_unavailable_when_flag_false() -> None:
    prompts = _prompts_module()
    backend_info = _backend_info_cls()
    manifest = {
        "numba": backend_info(
            name="numba",
            tier=1,
            strengths=["JIT"],
            limitations=["objs"],
            ast_patterns=[],
            best_for=["loops"],
            performance_range=(10.0, 200.0),
            install_hint="pip install numba",
            is_available=True,
        ),
        "taichi": backend_info(
            name="taichi",
            tier=3,
            strengths=["GPU"],
            limitations=["py version"],
            ast_patterns=[],
            best_for=["simulation"],
            performance_range=(10.0, 500.0),
            install_hint="pip install taichi",
            is_available=False,
            availability_reason="unsupported",
        ),
    }

    rendered = prompts.build_manifest_context(manifest, available_only=False)

    assert "numba" in rendered
    assert "taichi" in rendered
    assert "unsupported" in rendered


def test_generate_prompt_with_manifest_context_injection() -> None:
    optimizer = _optimizer_cls()()
    source = "def scalar_add(x):\n    return x + 1"
    manifest_context = "Backend manifest context:\n- numba\n- cython"

    prompt = optimizer.generate_prompt(
        source,
        _hotspot(),
        strategy="auto",
        manifest_context=manifest_context,
    )

    assert "Backend manifest context" in prompt
    assert "numba" in prompt
    assert "cython" in prompt


def test_generate_prompt_uses_specific_backend_no_manifest() -> None:
    optimizer = _optimizer_cls()()
    source = "def scalar_add(x):\n    return x + 1"
    manifest_context = "Backend manifest context:\n- numba\n- cython"

    prompt = optimizer.generate_prompt(
        source,
        _hotspot(),
        strategy="cython",
        manifest_context=manifest_context,
    )

    assert "typed memoryviews" in prompt
    assert "Backend manifest context" not in prompt


def test_optimize_function_accepts_strategy() -> None:
    default_optimizer = _optimizer_cls()

    class CaptureOptimizer(default_optimizer):
        def __init__(self) -> None:
            super().__init__()
            self.seen_strategy: str | None = None

        def generate_prompt(
            self,
            source_code: str,
            hotspot: Any,
            strategy: str = "auto",
            manifest_context: str | None = None,
        ) -> str:
            self.seen_strategy = strategy
            assert source_code
            assert hotspot.function_name
            assert manifest_context is None
            return "optimize this"

    optimizer = CaptureOptimizer()
    optimizer.provider = _MockProvider()

    source = "def compute_sum(data):\n    return sum(data)"
    attempt = optimizer.optimize_function(
        source,
        _hotspot(),
        config=_llm_config(),
        strategy="cython",
    )

    assert optimizer.seen_strategy == "cython"
    assert attempt.syntax_valid is True

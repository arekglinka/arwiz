from importlib import import_module

import pytest
from pydantic import ValidationError


def _backend_info_cls():
    return import_module("arwiz.foundation.types.backend").BackendInfo


def _optimization_strategy_cls():
    return import_module("arwiz.foundation.types.config").OptimizationStrategy


def _optimization_attempt_cls():
    return import_module("arwiz.foundation.types.optimization").OptimizationAttempt


class TestOptimizationStrategyBackends:
    def test_new_backend_values(self):
        OptimizationStrategy = _optimization_strategy_cls()  # noqa: N806
        assert OptimizationStrategy.CYTHON == "cython"
        assert OptimizationStrategy.JAX == "jax"
        assert OptimizationStrategy.CUPY == "cupy"
        assert OptimizationStrategy.NUMEXPR == "numexpr"
        assert OptimizationStrategy.PYO3 == "pyo3"
        assert OptimizationStrategy.CFFI == "cffi"
        assert OptimizationStrategy.TAICHI == "taichi"


class TestOptimizationAttemptBackendField:
    def test_accepts_backend_field(self):
        OptimizationAttempt = _optimization_attempt_cls()  # noqa: N806
        attempt = OptimizationAttempt(
            attempt_id="opt_backend_001",
            original_code="x = sum(data)",
            optimized_code="x = np.sum(data)",
            strategy="template",
            backend="cython",
        )

        assert attempt.backend == "cython"


class TestBackendInfo:
    def test_valid_backend_info(self):
        BackendInfo = _backend_info_cls()  # noqa: N806
        info = BackendInfo(
            name="cython",
            tier=1,
            strengths=["typed memoryviews", "aot compilation"],
            limitations=["requires c compiler"],
            ast_patterns=["for_loop", "array_indexing"],
            best_for=["numeric loops", "medium arrays"],
            performance_range=(10.0, 100.0),
            install_hint="pip install cython",
        )

        assert info.name == "cython"
        assert info.tier == 1
        assert info.performance_range == (10.0, 100.0)
        assert info.is_available is True
        assert info.availability_reason is None

    def test_rejects_invalid_tier_below_range(self):
        BackendInfo = _backend_info_cls()  # noqa: N806
        with pytest.raises(ValidationError):
            BackendInfo(
                name="jax",
                tier=0,
                strengths=["xla jit"],
                limitations=["jit warmup"],
                ast_patterns=["numpy_calls"],
                best_for=["large arrays"],
                performance_range=(5.0, 100.0),
                install_hint="pip install jax jaxlib",
            )

    def test_rejects_invalid_tier_above_range(self):
        BackendInfo = _backend_info_cls()  # noqa: N806
        with pytest.raises(ValidationError):
            BackendInfo(
                name="experimental",
                tier=4,
                strengths=["demo"],
                limitations=["not real"],
                ast_patterns=["none"],
                best_for=["none"],
                performance_range=(1.0, 2.0),
                install_hint="n/a",
            )

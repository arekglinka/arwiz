"""Tests for arwiz.foundation.types.optimization models."""

from arwiz.foundation.types.optimization import OptimizationAttempt, OptimizationResult


class TestOptimizationAttempt:
    def test_create_minimal(self):
        attempt = OptimizationAttempt(
            attempt_id="opt_001",
            original_code="x = sum(data)",
            optimized_code="x = np.sum(data)",
            strategy="numpy_vectorize",
        )
        assert attempt.attempt_id == "opt_001"
        assert attempt.original_code == "x = sum(data)"
        assert attempt.optimized_code == "x = np.sum(data)"
        assert attempt.strategy == "numpy_vectorize"
        assert attempt.llm_model is None
        assert attempt.template_name is None
        assert attempt.syntax_valid is False
        assert attempt.passed_equivalence is False
        assert attempt.speedup_percent == 0.0
        assert attempt.error_message is None

    def test_full_attempt(self):
        attempt = OptimizationAttempt(
            attempt_id="opt_002",
            original_code="def f(x):\n    return [i*2 for i in x]",
            optimized_code="@jit\nndef f(x):\n    return x * 2",
            strategy="numba_jit",
            syntax_valid=True,
            passed_equivalence=True,
            speedup_percent=75.5,
            timestamp="2025-01-01T00:00:00Z",
        )
        assert attempt.syntax_valid is True
        assert attempt.passed_equivalence is True
        assert attempt.speedup_percent == 75.5
        assert attempt.timestamp == "2025-01-01T00:00:00Z"

    def test_llm_attempt(self):
        attempt = OptimizationAttempt(
            attempt_id="opt_003",
            original_code="x = y",
            optimized_code="x = y",
            strategy="llm_generated",
            llm_model="gpt-4o",
            error_message="No improvement possible",
            timestamp="2025-01-01T00:00:00Z",
        )
        assert attempt.llm_model == "gpt-4o"
        assert attempt.error_message == "No improvement possible"

    def test_template_attempt(self):
        attempt = OptimizationAttempt(
            attempt_id="opt_004",
            original_code="x = [i**2 for i in range(n)]",
            optimized_code="import numpy as np\nx = np.arange(n)**2",
            strategy="template",
            template_name="list_comprehension_to_numpy",
            syntax_valid=True,
            passed_equivalence=True,
            speedup_percent=30.0,
            timestamp="2025-01-01T00:00:00Z",
        )
        assert attempt.template_name == "list_comprehension_to_numpy"

    def test_timestamp_auto_generated(self):
        attempt = OptimizationAttempt(
            attempt_id="opt_005",
            original_code="x = 1",
            optimized_code="x = 1",
            strategy="auto",
        )
        assert attempt.timestamp is not None


class TestOptimizationResult:
    def test_create_minimal(self):
        result = OptimizationResult(
            function_name="slow_func",
            file_path="module.py",
        )
        assert result.function_name == "slow_func"
        assert result.file_path == "module.py"
        assert result.attempts == []
        assert result.best_attempt is None
        assert result.applied is False
        assert result.total_time_saved_ms == 0.0

    def test_with_attempts(self):
        a1 = OptimizationAttempt(
            attempt_id="opt_1",
            original_code="x = sum(data)",
            optimized_code="x = np.sum(data)",
            strategy="numpy_vectorize",
            syntax_valid=True,
            passed_equivalence=True,
            speedup_percent=50.0,
            timestamp="2025-01-01T00:00:00Z",
        )
        a2 = OptimizationAttempt(
            attempt_id="opt_2",
            original_code="x = sum(data)",
            optimized_code="x = np.sum(data)",
            strategy="numba_jit",
            syntax_valid=True,
            passed_equivalence=True,
            speedup_percent=80.0,
            timestamp="2025-01-01T00:01:00Z",
        )
        result = OptimizationResult(
            function_name="slow_func",
            file_path="module.py",
            attempts=[a1, a2],
            best_attempt=a2,
            applied=True,
            total_time_saved_ms=400.0,
        )
        assert len(result.attempts) == 2
        assert result.best_attempt.attempt_id == "opt_2"
        assert result.applied is True
        assert result.total_time_saved_ms == 400.0

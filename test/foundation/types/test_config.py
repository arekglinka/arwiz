"""Tests for arwiz.foundation.types.config models."""

from arwiz.foundation.types.config import (
    ArwizConfig,
    LLMConfig,
    OptimizationStrategy,
    ProfilerType,
    ProfilingConfig,
)


class TestProfilerType:
    def test_values(self):
        assert ProfilerType.CPYTHON == "cprofile"
        assert ProfilerType.LINE == "line_profiler"
        assert ProfilerType.PYSPY == "py_spy"

    def test_is_str_enum(self):
        assert isinstance(ProfilerType.CPYTHON, str)


class TestOptimizationStrategy:
    def test_values(self):
        assert OptimizationStrategy.AUTO == "auto"
        assert OptimizationStrategy.LLM == "llm"
        assert OptimizationStrategy.TEMPLATE == "template"
        assert OptimizationStrategy.NUMPY == "numpy"
        assert OptimizationStrategy.NUMBA == "numba"


class TestArwizConfig:
    def test_defaults(self):
        cfg = ArwizConfig()
        assert cfg.target_python == "3.13"
        assert cfg.memory_limit_mb is None
        assert cfg.timeout_seconds == 300
        assert cfg.speedup_threshold_percent == 50.0
        assert cfg.equivalence_tolerance == 1e-6
        assert cfg.max_optimization_attempts == 5
        assert cfg.input_storage_path == ".arwiz/inputs"
        assert cfg.profile_storage_path == ".arwiz/profiles"
        assert cfg.cache_path == ".arwiz/cache"

    def test_override(self):
        cfg = ArwizConfig(timeout_seconds=60, speedup_threshold_percent=20.0)
        assert cfg.timeout_seconds == 60
        assert cfg.speedup_threshold_percent == 20.0

    def test_memory_limit_explicit(self):
        cfg = ArwizConfig(memory_limit_mb=512)
        assert cfg.memory_limit_mb == 512


class TestProfilingConfig:
    def test_defaults(self):
        cfg = ProfilingConfig()
        assert cfg.profiler_type == ProfilerType.CPYTHON
        assert cfg.line_profiling is False
        assert cfg.warmup_runs == 1
        assert cfg.min_function_time_pct == 5.0

    def test_override(self):
        cfg = ProfilingConfig(
            profiler_type=ProfilerType.LINE,
            line_profiling=True,
            warmup_runs=3,
        )
        assert cfg.profiler_type == ProfilerType.LINE
        assert cfg.line_profiling is True
        assert cfg.warmup_runs == 3


class TestLLMConfig:
    def test_defaults(self):
        cfg = LLMConfig()
        assert cfg.provider == "openai"
        assert cfg.model == "gpt-4o"
        assert cfg.api_key_env_var == "OPENAI_API_KEY"
        assert cfg.base_url is None
        assert cfg.max_tokens == 4096
        assert cfg.temperature == 0.2

    def test_anthropic_config(self):
        cfg = LLMConfig(
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            api_key_env_var="ANTHROPIC_API_KEY",
            max_tokens=8192,
            temperature=0.1,
        )
        assert cfg.provider == "anthropic"
        assert cfg.model == "claude-3-5-sonnet-20241022"
        assert cfg.api_key_env_var == "ANTHROPIC_API_KEY"
        assert cfg.max_tokens == 8192
        assert cfg.temperature == 0.1

    def test_ollama_with_base_url(self):
        cfg = LLMConfig(
            provider="ollama",
            model="llama3",
            base_url="http://localhost:11434",
            api_key_env_var="OLLAMA_API_KEY",
        )
        assert cfg.provider == "ollama"
        assert cfg.base_url == "http://localhost:11434"

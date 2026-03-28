from enum import StrEnum

from pydantic import BaseModel


class ProfilerType(StrEnum):
    CPYTHON = "cprofile"
    LINE = "line_profiler"
    PYSPY = "py_spy"


class OptimizationStrategy(StrEnum):
    AUTO = "auto"
    LLM = "llm"
    TEMPLATE = "template"
    NUMPY = "numpy"
    NUMBA = "numba"
    CYTHON = "cython"
    JAX = "jax"
    CUPY = "cupy"
    NUMEXPR = "numexpr"
    PYO3 = "pyo3"
    CFFI = "cffi"
    TAICHI = "taichi"


class LLMConfig(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4o"
    api_key_env_var: str = "OPENAI_API_KEY"
    api_key: str | None = None
    base_url: str | None = None
    max_tokens: int = 4096
    temperature: float = 0.2


class ArwizConfig(BaseModel):
    target_python: str = "3.13"
    memory_limit_mb: int | None = None
    timeout_seconds: int = 300
    speedup_threshold_percent: float = 50.0
    equivalence_tolerance: float = 1e-6
    max_optimization_attempts: int = 5
    input_storage_path: str = ".arwiz/inputs"
    profile_storage_path: str = ".arwiz/profiles"
    cache_path: str = ".arwiz/cache"
    llm_config: LLMConfig = LLMConfig()


class ProfilingConfig(BaseModel):
    profiler_type: ProfilerType = ProfilerType.CPYTHON
    line_profiling: bool = False
    warmup_runs: int = 1
    min_function_time_pct: float = 5.0

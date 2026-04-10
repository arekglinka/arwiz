import warnings
from importlib import import_module

import pytest


def _hotspot_type():
    return import_module("arwiz.foundation").HotSpot


def _optimizer_type():
    return import_module("arwiz.template_optimizer.core").DefaultTemplateOptimizer


def _detect_for_loops(source: str):
    return import_module("arwiz.template_optimizer.pattern_detection").detect_for_loops(source)


def test_list_templates_returns_12() -> None:
    optimizer = _optimizer_type()()
    assert set(optimizer.list_templates()) == {
        "add_caching",
        "batch_io",
        "cffi_optimize",
        "cupy_optimize",
        "cython_optimize",
        "jax_optimize",
        "numexpr_optimize",
        "numba_jit",
        "numba_parallel",
        "pyo3_optimize",
        "taichi_optimize",
        "vectorize_loop",
    }


def test_detect_applicable_finds_loops() -> None:
    source = """
def compute(n):
    total = 0
    for i in range(n):
        total += i
    return total
"""
    hotspot = _hotspot_type()(
        function_name="compute",
        file_path="/tmp/test.py",
        line_range=(1, 5),
        cumulative_time_ms=22,
        self_time_ms=20,
        call_count=10,
    )
    optimizer = _optimizer_type()()
    detected = optimizer.detect_applicable_templates(source, hotspot)
    assert "vectorize_loop" in detected


def test_apply_vectorize_transforms_simple() -> None:
    source = """
def compute(n):
    total = 0
    for i in range(n):
        total += i
    return total
"""
    optimizer = _optimizer_type()()
    transformed = optimizer.apply_template(source, "vectorize_loop")
    assert "numpy" in transformed or "np." in transformed


def test_apply_numba_jit_adds_decorator() -> None:
    source = """
def f(x):
    return x + 1
"""
    optimizer = _optimizer_type()()
    transformed = optimizer.apply_template(source, "numba_jit")
    assert "@numba.njit" in transformed


def test_apply_numba_parallel_adds_parallel_and_prange() -> None:
    source = """
def f(arr):
    out = arr.copy()
    for i in range(len(arr)):
        out[i] = arr[i] * 2
    return out
"""
    optimizer = _optimizer_type()()
    transformed = optimizer.apply_template(source, "numba_parallel")
    assert "@numba.njit(parallel=True)" in transformed
    assert "numba.prange(" in transformed


def test_apply_numba_parallel_skips_dependent_loop_prange_rewrite() -> None:
    source = """
def prefix_sum(arr):
    out = arr.copy()
    for i in range(1, len(arr)):
        out[i] = out[i - 1] + arr[i]
    return out
"""
    optimizer = _optimizer_type()()
    transformed = optimizer.apply_template(source, "numba_parallel")
    assert "@numba.njit(parallel=True)" in transformed
    assert "for i in range(" in transformed
    assert "numba.prange(" not in transformed


def test_apply_add_caching_adds_decorator() -> None:
    source = """
def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)
"""
    optimizer = _optimizer_type()()
    transformed = optimizer.apply_template(source, "add_caching")
    assert "@functools.lru_cache(maxsize=None)" in transformed


def test_apply_batch_io_has_comment() -> None:
    source = """
def writer(path, items):
    with open(path, "w") as f:
        for item in items:
            f.write(str(item))
"""
    optimizer = _optimizer_type()()
    transformed = optimizer.apply_template(source, "batch_io")
    assert "join" in transformed or "buffer" in transformed


def test_unknown_template_raises() -> None:
    optimizer = _optimizer_type()()
    with pytest.raises(ValueError):
        optimizer.apply_template("def x():\n    return 1", "nonexistent")


def test_pattern_detection_finds_loops() -> None:
    source = """
for i in range(10):
    print(i)
"""
    assert len(_detect_for_loops(source)) == 1


def test_detect_applicable_templates_includes_numba_parallel_for_independent_loop() -> None:
    source = """
def compute(arr):
    out = arr.copy()
    for i in range(len(arr)):
        out[i] = arr[i] * 2
    return out
"""
    hotspot = _hotspot_type()(
        function_name="compute",
        file_path="/tmp/test.py",
        line_range=(1, 6),
        cumulative_time_ms=22,
        self_time_ms=20,
        call_count=1,
    )
    optimizer = _optimizer_type()()
    detected = optimizer.detect_applicable_templates(source, hotspot)
    assert "numba_parallel" in detected


def test_detect_applicable_templates_skips_numba_parallel_for_dependent_loop() -> None:
    source = """
def prefix_sum(arr):
    out = arr.copy()
    for i in range(1, len(arr)):
        out[i] = out[i - 1] + arr[i]
    return out
"""
    hotspot = _hotspot_type()(
        function_name="prefix_sum",
        file_path="/tmp/test.py",
        line_range=(1, 6),
        cumulative_time_ms=22,
        self_time_ms=20,
        call_count=1,
    )
    optimizer = _optimizer_type()()
    detected = optimizer.detect_applicable_templates(source, hotspot)
    assert "numba_jit" in detected
    assert "numba_parallel" not in detected


def test_build_numba_parallel_prompt_mentions_prange_and_independence() -> None:
    build_numba_parallel_prompt = import_module(
        "arwiz.llm_optimizer.prompts"
    ).build_numba_parallel_prompt

    source = "def f(arr):\n    return arr[0]\n"
    hotspot = _hotspot_type()(
        function_name="f",
        file_path="/tmp/f.py",
        line_range=(1, 2),
        cumulative_time_ms=10,
        self_time_ms=5,
        call_count=2,
    )
    prompt = build_numba_parallel_prompt(source, hotspot)
    assert "parallel=True" in prompt
    assert "prange" in prompt
    assert "independence" in prompt.lower() or "independent" in prompt.lower()


def test_generate_prompt_routes_numba_parallel_alias() -> None:
    optimizer = import_module("arwiz.llm_optimizer.core").DefaultLLMOptimizer()
    source = "def f(arr):\n    return arr[0]\n"
    hotspot = _hotspot_type()(
        function_name="f",
        file_path="/tmp/f.py",
        line_range=(1, 2),
        cumulative_time_ms=10,
        self_time_ms=5,
        call_count=2,
    )
    prompt = optimizer.generate_prompt(source, hotspot, strategy="numba-parallel")
    assert "parallel=True" in prompt
    assert "prange" in prompt
    assert "Strategy hint:" in prompt


def test_vectorized_output_valid_python() -> None:
    source = """
def compute(n):
    total = 0
    for i in range(n):
        total += i
    return total
"""
    optimizer = _optimizer_type()()
    transformed = optimizer.apply_template(source, "vectorize_loop")
    compile(transformed, "<string>", "exec")


def test_add_caching_warns_on_unhashable_params() -> None:
    source = "def process(data: list[int]) -> int:\n    return len(data)\n"
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        apply_add_caching = import_module(
            "arwiz.template_optimizer.templates.add_caching"
        ).apply_add_caching

        apply_add_caching(source)
        assert len(w) == 1
        assert "unhashable" in str(w[0].message).lower()
        assert "process" in str(w[0].message)


def test_apply_cython_optimize_adds_directives_and_import() -> None:
    source = """
def accumulate(arr):
    total = 0.0
    for i in range(len(arr)):
        total += arr[i]
    return total
"""
    optimizer = _optimizer_type()()
    transformed = optimizer.apply_template(source, "cython_optimize")
    assert "# cython: boundscheck=False, wraparound=False" in transformed
    assert "import cython" in transformed
    assert "@cython.cfunc" in transformed


def test_apply_cython_optimize_rewrites_loop_var_and_memoryview_annotation() -> None:
    source = """
def scale(values):
    out = []
    for i in range(len(values)):
        out.append(values[i] * 2.0)
    return out
"""
    optimizer = _optimizer_type()()
    transformed = optimizer.apply_template(source, "cython_optimize")
    assert "i: cython.int" in transformed
    assert "values: cython.double[:]" in transformed


def test_detect_applicable_templates_adds_cython_optimize_for_loop_indexing_pattern() -> None:
    source = """
def norm(arr):
    total = 0.0
    for i in range(len(arr)):
        total += arr[i]
    return total
"""
    optimizer = _optimizer_type()()
    detected = optimizer.detect_applicable_templates(source)
    assert "cython_optimize" in detected


def test_build_cython_prompt_contains_memoryview_guidance() -> None:
    build_cython_prompt = import_module("arwiz.llm_optimizer.prompts").build_cython_prompt

    source = "def f(arr):\n    return arr[0]\n"
    hotspot = _hotspot_type()(
        function_name="f",
        file_path="/tmp/f.py",
        line_range=(1, 2),
        cumulative_time_ms=10,
        self_time_ms=5,
        call_count=2,
    )
    prompt = build_cython_prompt(source, hotspot)
    assert "Optimize this Python function using Cython typed memoryviews" in prompt
    assert "boundscheck=False" in prompt
    assert "wraparound=False" in prompt


def test_generate_prompt_routes_cython_alias() -> None:
    optimizer = import_module("arwiz.llm_optimizer.core").DefaultLLMOptimizer()
    source = "def f(arr):\n    return arr[0]\n"
    hotspot = _hotspot_type()(
        function_name="f",
        file_path="/tmp/f.py",
        line_range=(1, 2),
        cumulative_time_ms=10,
        self_time_ms=5,
        call_count=2,
    )
    prompt = optimizer.generate_prompt(source, hotspot, strategy="typed_memoryview")
    assert "Optimize this Python function using Cython typed memoryviews" in prompt
    assert "Strategy hint:" in prompt


def test_apply_numexpr_optimize_rewrites_simple_elementwise_loop() -> None:
    source = """
def norm2(a, b):
    result = a.copy()
    for i in range(len(a)):
        result[i] = a[i] ** 2 + b[i] ** 2
    return result
"""
    optimizer = _optimizer_type()()
    transformed = optimizer.apply_template(source, "numexpr_optimize")
    assert "import numexpr" in transformed
    assert "numexpr.evaluate" in transformed
    assert '"a ** 2 + b ** 2"' in transformed or "'a ** 2 + b ** 2'" in transformed


def test_apply_numexpr_optimize_noop_when_not_simple_loop_assignment() -> None:
    source = """
def accumulate(a, b):
    total = 0.0
    for i in range(len(a)):
        total += a[i] * b[i]
    return total
"""
    optimizer = _optimizer_type()()
    transformed = optimizer.apply_template(source, "numexpr_optimize")
    assert transformed.strip() == source.strip()


def test_detect_applicable_templates_adds_numexpr_for_arithmetic_index_loop() -> None:
    source = """
def norm2(a, b):
    result = a.copy()
    for i in range(len(a)):
        result[i] = a[i] ** 2 + b[i] ** 2
    return result
"""
    optimizer = _optimizer_type()()
    detected = optimizer.detect_applicable_templates(source)
    assert "numexpr_optimize" in detected


def test_build_numexpr_prompt_contains_numexpr_guidance() -> None:
    build_numexpr_prompt = import_module("arwiz.llm_optimizer.prompts").build_numexpr_prompt

    source = "def f(a, b):\n    return a + b\n"
    hotspot = _hotspot_type()(
        function_name="f",
        file_path="/tmp/f.py",
        line_range=(1, 2),
        cumulative_time_ms=10,
        self_time_ms=5,
        call_count=2,
    )
    prompt = build_numexpr_prompt(source, hotspot)
    assert "NumExpr" in prompt or "numexpr" in prompt
    assert "numexpr.evaluate" in prompt


def test_generate_prompt_routes_numexpr_alias() -> None:
    optimizer = import_module("arwiz.llm_optimizer.core").DefaultLLMOptimizer()
    source = "def f(a, b):\n    return a + b\n"
    hotspot = _hotspot_type()(
        function_name="f",
        file_path="/tmp/f.py",
        line_range=(1, 2),
        cumulative_time_ms=10,
        self_time_ms=5,
        call_count=2,
    )
    prompt = optimizer.generate_prompt(source, hotspot, strategy="numexpr-evaluate")
    assert "numexpr.evaluate" in prompt
    assert "Strategy hint:" in prompt


def test_list_templates_includes_cupy_template() -> None:
    optimizer = _optimizer_type()()
    templates = set(optimizer.list_templates())
    assert {
        "add_caching",
        "batch_io",
        "cython_optimize",
        "numba_jit",
        "numba_parallel",
        "vectorize_loop",
        "cupy_optimize",
    }.issubset(templates)


def test_apply_cupy_optimize_rewrites_numpy_alias_and_adds_transfers() -> None:
    source = """
import numpy as np

def gpu_sum(arr):
    values = np.array(arr)
    return np.sum(values)
"""
    optimizer = _optimizer_type()()
    transformed = optimizer.apply_template(source, "cupy_optimize")
    assert "import cupy as cp" in transformed
    assert "cp.asarray(arr)" in transformed
    assert "cp.array" in transformed
    assert "cp.sum" in transformed
    assert "cp.asnumpy(" in transformed


def test_detect_applicable_templates_adds_cupy_for_numpy_code() -> None:
    source = """
import numpy as np

def norm(arr):
    return np.sum(np.array(arr) * 2)
"""
    optimizer = _optimizer_type()()
    detected = optimizer.detect_applicable_templates(source)
    assert "cupy_optimize" in detected


def test_build_cupy_prompt_contains_gpu_transfer_guidance() -> None:
    build_cupy_prompt = import_module("arwiz.llm_optimizer.prompts").build_cupy_prompt

    source = "def f(arr):\n    return arr\n"
    hotspot = _hotspot_type()(
        function_name="f",
        file_path="/tmp/f.py",
        line_range=(1, 2),
        cumulative_time_ms=10,
        self_time_ms=5,
        call_count=2,
    )
    prompt = build_cupy_prompt(source, hotspot)
    assert "CuPy" in prompt
    assert "cp.asarray" in prompt
    assert "cp.asnumpy" in prompt


def test_generate_prompt_routes_cupy_aliases() -> None:
    optimizer = import_module("arwiz.llm_optimizer.core").DefaultLLMOptimizer()
    source = "def f(arr):\n    return arr\n"
    hotspot = _hotspot_type()(
        function_name="f",
        file_path="/tmp/f.py",
        line_range=(1, 2),
        cumulative_time_ms=10,
        self_time_ms=5,
        call_count=2,
    )
    prompt = optimizer.generate_prompt(source, hotspot, strategy="cupy-gpu")
    assert "CuPy" in prompt
    assert "Strategy hint:" in prompt


def test_apply_jax_optimize_rewrites_numpy_import_calls_and_adds_jit() -> None:
    source = """
import numpy as np

def compute(arr):
    return np.sum(arr)
"""
    optimizer = _optimizer_type()()
    transformed = optimizer.apply_template(source, "jax_optimize")
    assert "import jax.numpy as jnp" in transformed
    assert "import numpy as np" not in transformed
    assert "import jax" in transformed
    assert "@jax.jit" in transformed
    assert "jnp.sum(arr)" in transformed


def test_detect_applicable_templates_adds_jax_optimize_for_numpy_array_ops() -> None:
    source = """
import numpy as np

def compute(arr):
    return np.sqrt(arr)
"""
    optimizer = _optimizer_type()()
    detected = optimizer.detect_applicable_templates(source)
    assert "jax_optimize" in detected


def test_build_jax_prompt_contains_jit_guidance() -> None:
    build_jax_prompt = import_module("arwiz.llm_optimizer.prompts").build_jax_prompt

    source = "def f(arr):\n    return arr\n"
    hotspot = _hotspot_type()(
        function_name="f",
        file_path="/tmp/f.py",
        line_range=(1, 2),
        cumulative_time_ms=10,
        self_time_ms=5,
        call_count=2,
    )
    prompt = build_jax_prompt(source, hotspot)
    assert "JAX" in prompt
    assert "jax.jit" in prompt


def test_generate_prompt_routes_jax_alias() -> None:
    optimizer = import_module("arwiz.llm_optimizer.core").DefaultLLMOptimizer()
    source = "def f(arr):\n    return arr\n"
    hotspot = _hotspot_type()(
        function_name="f",
        file_path="/tmp/f.py",
        line_range=(1, 2),
        cumulative_time_ms=10,
        self_time_ms=5,
        call_count=2,
    )
    prompt = optimizer.generate_prompt(source, hotspot, strategy="jax_jit")
    assert "jax.jit" in prompt
    assert "Strategy hint:" in prompt


# --- Taichi stub tests (Task 16) ---


def test_apply_taichi_optimize_returns_source_with_unavailability_comment() -> None:
    apply_taichi_optimize = import_module(
        "arwiz.template_optimizer.templates.taichi_optimize"
    ).apply_taichi_optimize
    source = (
        "def compute(n):\n    total = 0\n    for i in range(n):\n"
        "        total += i\n    return total\n"
    )
    result = apply_taichi_optimize(source)
    assert "Taichi" in result
    assert "Python 3.12" in result
    assert "unavailable" in result.lower()
    assert "def compute(n):" in result
    assert "total += i" in result


def test_apply_taichi_optimize_does_not_transform_source() -> None:
    apply_taichi_optimize = import_module(
        "arwiz.template_optimizer.templates.taichi_optimize"
    ).apply_taichi_optimize
    source = "def f(x):\n    return x + 1\n"
    result = apply_taichi_optimize(source)
    assert "def f(x):" in result
    assert "return x + 1" in result


def test_taichi_manifest_is_unavailable() -> None:
    manifest = import_module("arwiz.backend_selector.manifest").BackendManifest()
    available, reason = manifest.check_availability("taichi")
    assert available is False
    assert "3.12" in reason or "3.10" in reason


def test_taichi_not_detected_in_applicable_templates() -> None:
    source = """
def compute(n):
    total = 0
    for i in range(n):
        total += i
    return total
"""
    optimizer = _optimizer_type()()
    detected = optimizer.detect_applicable_templates(source)
    assert "taichi_optimize" not in detected


def test_build_taichi_prompt_mentions_unavailability() -> None:
    build_taichi_prompt = import_module("arwiz.llm_optimizer.prompts").build_taichi_prompt

    source = "def f(arr):\n    return arr[0]\n"
    hotspot = _hotspot_type()(
        function_name="f",
        file_path="/tmp/f.py",
        line_range=(1, 2),
        cumulative_time_ms=10,
        self_time_ms=5,
        call_count=2,
    )
    prompt = build_taichi_prompt(source, hotspot)
    assert "Taichi" in prompt
    assert "unavailable" in prompt.lower() or "3.10" in prompt or "3.12" in prompt


def test_generate_prompt_routes_taichi_with_unavailability_message() -> None:
    optimizer = import_module("arwiz.llm_optimizer.core").DefaultLLMOptimizer()
    source = "def f(arr):\n    return arr[0]\n"
    hotspot = _hotspot_type()(
        function_name="f",
        file_path="/tmp/f.py",
        line_range=(1, 2),
        cumulative_time_ms=10,
        self_time_ms=5,
        call_count=2,
    )
    prompt = optimizer.generate_prompt(source, hotspot, strategy="taichi")
    assert "Taichi" in prompt
    assert "unavailable" in prompt.lower() or "3.10" in prompt or "3.12" in prompt


def test_apply_cffi_optimize_numeric_loop_generates_cffi_bindings() -> None:
    apply_cffi_optimize = import_module(
        "arwiz.template_optimizer.templates.cffi_optimize"
    ).apply_cffi_optimize

    source = """
def dot_like(a, b, n):
    total = 0.0
    for i in range(n):
        total += a[i] * b[i]
    return total
"""
    transformed = apply_cffi_optimize(source)
    assert "from cffi import FFI" in transformed
    assert "ffi = FFI()" in transformed
    assert "ffi.cdef(" in transformed
    assert "ffi.verify(" in transformed
    assert "def dot_like(a, b, n):" in transformed
    compile(transformed, "<string>", "exec")


def test_apply_cffi_optimize_non_numeric_adds_guidance_comment() -> None:
    apply_cffi_optimize = import_module(
        "arwiz.template_optimizer.templates.cffi_optimize"
    ).apply_cffi_optimize

    source = """
def greet(name):
    return f\"Hello {name}\"
"""
    transformed = apply_cffi_optimize(source)
    assert "CFFI is most useful for calling existing C libraries" in transformed
    compile(transformed, "<string>", "exec")


def test_detect_applicable_templates_adds_cffi_for_numeric_loop_pattern() -> None:
    source = """
def accumulate(arr):
    total = 0.0
    for i in range(len(arr)):
        total += arr[i] * 2.0
    return total
"""
    optimizer = _optimizer_type()()
    detected = optimizer.detect_applicable_templates(source)
    assert "cffi_optimize" in detected


def test_build_cffi_prompt_contains_cffi_guidance() -> None:
    build_cffi_prompt = import_module("arwiz.llm_optimizer.prompts").build_cffi_prompt

    source = "def f(a):\n    return a\n"
    hotspot = _hotspot_type()(
        function_name="f",
        file_path="/tmp/f.py",
        line_range=(1, 2),
        cumulative_time_ms=10,
        self_time_ms=5,
        call_count=2,
    )
    prompt = build_cffi_prompt(source, hotspot)
    assert "CFFI" in prompt
    assert "ffi.cdef" in prompt
    assert "ffi.verify" in prompt


def test_generate_prompt_routes_cffi_aliases() -> None:
    optimizer = import_module("arwiz.llm_optimizer.core").DefaultLLMOptimizer()
    source = "def f(a):\n    return a\n"
    hotspot = _hotspot_type()(
        function_name="f",
        file_path="/tmp/f.py",
        line_range=(1, 2),
        cumulative_time_ms=10,
        self_time_ms=5,
        call_count=2,
    )
    prompt = optimizer.generate_prompt(source, hotspot, strategy="ffi")
    assert "CFFI" in prompt
    assert "Strategy hint:" in prompt


def test_apply_pyo3_optimize_generates_rust_pyfunction_for_string_workloads() -> None:
    source = """
def normalize_text(text):
    return text.strip().lower().replace("-", "_")
"""
    optimizer = _optimizer_type()()
    transformed = optimizer.apply_template(source, "pyo3_optimize")
    assert "use pyo3::prelude::*;" in transformed
    assert "#[pyfunction]" in transformed
    assert "maturin develop" in transformed
    assert "normalize_text" in transformed


def test_apply_pyo3_optimize_adds_non_string_guidance_comment_when_not_string_heavy() -> None:
    source = """
def sum_values(values):
    total = 0
    for value in values:
        total += value
    return total
"""
    optimizer = _optimizer_type()()
    transformed = optimizer.apply_template(source, "pyo3_optimize")
    assert "Rust" in transformed
    assert "string" in transformed.lower()
    assert "single-thread" in transformed.lower()


def test_apply_pyo3_optimize_never_crashes_on_invalid_input() -> None:
    optimizer = _optimizer_type()()
    transformed = optimizer.apply_template("def broken(:\n    pass", "pyo3_optimize")
    assert isinstance(transformed, str)
    assert transformed


def test_detect_applicable_templates_adds_pyo3_for_string_operations() -> None:
    source = """
def parse_name(raw):
    parts = raw.split(":")
    return parts[0].replace(" ", "_")
"""
    optimizer = _optimizer_type()()
    detected = optimizer.detect_applicable_templates(source)
    assert "pyo3_optimize" in detected


def test_build_pyo3_prompt_contains_rust_guidance() -> None:
    build_pyo3_prompt = import_module("arwiz.llm_optimizer.prompts").build_pyo3_prompt

    source = "def parse_name(raw):\n    return raw.split(':')[0]\n"
    hotspot = _hotspot_type()(
        function_name="parse_name",
        file_path="/tmp/f.py",
        line_range=(1, 2),
        cumulative_time_ms=10,
        self_time_ms=5,
        call_count=2,
    )
    prompt = build_pyo3_prompt(source, hotspot)
    assert "PyO3" in prompt or "pyo3" in prompt
    assert "Rust" in prompt
    assert "Target function: parse_name" in prompt


def test_generate_prompt_routes_pyo3_and_rust_aliases() -> None:
    optimizer = import_module("arwiz.llm_optimizer.core").DefaultLLMOptimizer()
    source = "def parse_name(raw):\n    return raw.split(':')[0]\n"
    hotspot = _hotspot_type()(
        function_name="parse_name",
        file_path="/tmp/f.py",
        line_range=(1, 2),
        cumulative_time_ms=10,
        self_time_ms=5,
        call_count=2,
    )
    prompt = optimizer.generate_prompt(source, hotspot, strategy="rust")
    assert "PyO3" in prompt or "pyo3" in prompt
    assert "Strategy hint:" in prompt

import warnings

import pytest
from arwiz.foundation import HotSpot
from arwiz.template_optimizer.core import DefaultTemplateOptimizer
from arwiz.template_optimizer.pattern_detection import detect_for_loops


def test_list_templates_returns_4() -> None:
    optimizer = DefaultTemplateOptimizer()
    assert set(optimizer.list_templates()) == {
        "add_caching",
        "batch_io",
        "numba_jit",
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
    hotspot = HotSpot(
        function_name="compute",
        file_path="/tmp/test.py",
        line_range=(1, 5),
        cumulative_time_ms=22,
        self_time_ms=20,
        call_count=10,
    )
    optimizer = DefaultTemplateOptimizer()
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
    optimizer = DefaultTemplateOptimizer()
    transformed = optimizer.apply_template(source, "vectorize_loop")
    assert "numpy" in transformed or "np." in transformed


def test_apply_numba_jit_adds_decorator() -> None:
    source = """
def f(x):
    return x + 1
"""
    optimizer = DefaultTemplateOptimizer()
    transformed = optimizer.apply_template(source, "numba_jit")
    assert "@numba.njit" in transformed


def test_apply_add_caching_adds_decorator() -> None:
    source = """
def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)
"""
    optimizer = DefaultTemplateOptimizer()
    transformed = optimizer.apply_template(source, "add_caching")
    assert "@functools.lru_cache(maxsize=None)" in transformed


def test_apply_batch_io_has_comment() -> None:
    source = """
def writer(path, items):
    with open(path, "w") as f:
        for item in items:
            f.write(str(item))
"""
    optimizer = DefaultTemplateOptimizer()
    transformed = optimizer.apply_template(source, "batch_io")
    assert "join" in transformed or "buffer" in transformed


def test_unknown_template_raises() -> None:
    optimizer = DefaultTemplateOptimizer()
    with pytest.raises(ValueError):
        optimizer.apply_template("def x():\n    return 1", "nonexistent")


def test_pattern_detection_finds_loops() -> None:
    source = """
for i in range(10):
    print(i)
"""
    assert len(detect_for_loops(source)) == 1


def test_vectorized_output_valid_python() -> None:
    source = """
def compute(n):
    total = 0
    for i in range(n):
        total += i
    return total
"""
    optimizer = DefaultTemplateOptimizer()
    transformed = optimizer.apply_template(source, "vectorize_loop")
    compile(transformed, "<string>", "exec")


def test_add_caching_warns_on_unhashable_params() -> None:
    source = "def process(data: list[int]) -> int:\n    return len(data)\n"
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        from arwiz.template_optimizer.templates.add_caching import apply_add_caching

        apply_add_caching(source)
        assert len(w) == 1
        assert "unhashable" in str(w[0].message).lower()
        assert "process" in str(w[0].message)

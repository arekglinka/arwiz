import sys
from pathlib import Path

import pytest
from arwiz.hot_reload.core import DefaultHotReloader

TARGETS_DIR = Path(__file__).parent.parent / "fixtures" / "targets"


@pytest.fixture(scope="module", autouse=True)
def _add_targets_to_path():
    str_dir = str(TARGETS_DIR)
    if str_dir not in sys.path:
        sys.path.insert(0, str_dir)
    yield
    if "simple_loop" in sys.modules:
        del sys.modules["simple_loop"]


@pytest.fixture(scope="module")
def simple_loop_path() -> Path:
    return TARGETS_DIR / "simple_loop.py"


def test_reload_function_success(simple_loop_path):
    reloader = DefaultHotReloader()
    import simple_loop

    new_source = """
def compute_sum(data):
    return sum(x * x for x in data)
"""
    result = reloader.reload_function(simple_loop_path, "compute_sum", new_source)
    assert result is True
    assert simple_loop.compute_sum([1, 2, 3]) == 14
    reloader.rollback(simple_loop_path, "compute_sum")


def test_reload_function_invalid_syntax(simple_loop_path):
    reloader = DefaultHotReloader()
    new_source = "def broken(\n"
    result = reloader.reload_function(simple_loop_path, "compute_sum", new_source)
    assert result is False


def test_create_wrapper_falls_back():
    reloader = DefaultHotReloader()

    def original(x):
        return x * 2

    def optimized(x):
        raise ValueError("optimized failed")

    wrapper = reloader.create_function_wrapper(original, optimized)
    assert wrapper(5) == 10


def test_rollback_restores_original(simple_loop_path):
    reloader = DefaultHotReloader()
    import simple_loop

    original_fn = simple_loop.compute_sum

    new_source = """
def compute_sum(data):
    return 999
"""
    reloader.reload_function(simple_loop_path, "compute_sum", new_source)
    assert simple_loop.compute_sum([1, 2, 3]) == 999

    reloader.rollback(simple_loop_path, "compute_sum")
    assert simple_loop.compute_sum([1, 2, 3]) == original_fn([1, 2, 3])


def test_double_reload_and_rollback(simple_loop_path):
    reloader = DefaultHotReloader()
    import simple_loop

    original_fn = simple_loop.compute_sum

    reloader.reload_function(simple_loop_path, "compute_sum", "def compute_sum(data): return 1")
    assert simple_loop.compute_sum([]) == 1

    reloader.reload_function(simple_loop_path, "compute_sum", "def compute_sum(data): return 2")
    assert simple_loop.compute_sum([]) == 2

    reloader.rollback(simple_loop_path, "compute_sum")
    assert simple_loop.compute_sum([1, 2, 3]) == original_fn([1, 2, 3])

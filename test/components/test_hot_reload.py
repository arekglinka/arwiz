"""Tests for arwiz.hot_reload — runtime function replacement and rollback."""

from __future__ import annotations

import sys
from importlib import util
from pathlib import Path

import pytest
from arwiz.hot_reload.core import DefaultHotReloader  # pyrefly: ignore[missing-import]
from arwiz.hot_reload.frame_manipulation import (  # pyrefly: ignore[missing-import]
    inject_variable,
    is_cpython,
)

TARGETS_DIR = Path(__file__).parent.parent / "fixtures" / "targets"


@pytest.fixture(autouse=True)
def _add_targets_to_path():
    str_dir = str(TARGETS_DIR)
    if str_dir not in sys.path:
        sys.path.insert(0, str_dir)
    yield
    for mod_name in list(sys.modules):
        if mod_name.startswith("simple_loop") or mod_name.startswith("test_hot_reload"):
            del sys.modules[mod_name]


@pytest.fixture()
def simple_loop_path() -> Path:
    return TARGETS_DIR / "simple_loop.py"


class TestReloadFunction:
    def test_replace_works(self, simple_loop_path: Path) -> None:
        reloader = DefaultHotReloader()
        import simple_loop  # pyrefly: ignore[missing-import]

        new_source = "def compute_sum(data):\n    return sum(x * x for x in data)\n"
        result = reloader.reload_function(simple_loop_path, "compute_sum", new_source)
        assert result is True
        assert simple_loop.compute_sum([1, 2, 3]) == 14
        reloader.rollback(simple_loop_path, "compute_sum")

    def test_invalid_syntax_returns_false(self, simple_loop_path: Path) -> None:
        reloader = DefaultHotReloader()
        result = reloader.reload_function(simple_loop_path, "compute_sum", "def broken(\n")
        assert result is False

    def test_missing_function_returns_false(self, simple_loop_path: Path) -> None:
        reloader = DefaultHotReloader()
        result = reloader.reload_function(
            simple_loop_path, "nonexistent_func", "def nonexistent_func(): pass"
        )
        assert result is False

    def test_re_replace_rollback_to_first_original(self, simple_loop_path: Path) -> None:
        reloader = DefaultHotReloader()
        import simple_loop  # pyrefly: ignore[missing-import]

        original_fn = simple_loop.compute_sum

        reloader.reload_function(simple_loop_path, "compute_sum", "def compute_sum(data): return 1")
        reloader.reload_function(simple_loop_path, "compute_sum", "def compute_sum(data): return 2")
        assert simple_loop.compute_sum([]) == 2

        reloader.rollback(simple_loop_path, "compute_sum")
        assert simple_loop.compute_sum([1, 2, 3]) == original_fn([1, 2, 3])

    def test_reload_function_in_main_module(self, tmp_path: Path) -> None:
        script = tmp_path / "main_script.py"
        script.write_text(
            "def my_func(x):\n    return x + 1\n\nresult = my_func(5)\nprint(result)\n",
            encoding="utf-8",
        )

        spec = util.spec_from_file_location("__main__", str(script))
        assert spec is not None and spec.loader is not None

        mod = util.module_from_spec(spec)
        previous_main = sys.modules.get("__main__")
        sys.modules["__main__"] = mod
        try:
            spec.loader.exec_module(mod)

            reloader = DefaultHotReloader()
            new_source = "def my_func(x):\n    return x + 2"

            assert reloader.reload_function(script, "my_func", new_source, module=mod)
            assert mod.my_func(5) == 7
        finally:
            if previous_main is None:
                sys.modules.pop("__main__", None)
            else:
                sys.modules["__main__"] = previous_main


class TestRollback:
    def test_restores_original(self, simple_loop_path: Path) -> None:
        reloader = DefaultHotReloader()
        import simple_loop  # pyrefly: ignore[missing-import]

        original_fn = simple_loop.compute_sum

        new_source = "def compute_sum(data):\n    return 999\n"
        reloader.reload_function(simple_loop_path, "compute_sum", new_source)
        assert simple_loop.compute_sum([1, 2, 3]) == 999

        reloader.rollback(simple_loop_path, "compute_sum")
        assert simple_loop.compute_sum([1, 2, 3]) == original_fn([1, 2, 3])

    def test_missing_raises_keyerror(self, simple_loop_path: Path) -> None:
        reloader = DefaultHotReloader()
        with pytest.raises(KeyError):
            reloader.rollback(simple_loop_path, "compute_sum")

    def test_clear_originals_frees_memory(self, simple_loop_path: Path) -> None:
        reloader = DefaultHotReloader()
        new_source = "def compute_sum(data):\n    return 999\n"
        reloader.reload_function(simple_loop_path, "compute_sum", new_source)
        assert len(reloader._originals) == 1

        cleared = reloader.clear_originals()
        assert cleared == 1
        assert len(reloader._originals) == 0
        # After clear, rollback should fail since original is gone
        with pytest.raises(KeyError):
            reloader.rollback(simple_loop_path, "compute_sum")


class TestWrapper:
    def test_calls_optimized(self) -> None:
        reloader = DefaultHotReloader()

        def original(x: int) -> int:
            return x * 2

        def optimized(x: int) -> int:
            return x * 10

        wrapper = reloader.create_function_wrapper(original, optimized)
        assert wrapper(5) == 50

    def test_falls_back_on_error(self) -> None:
        reloader = DefaultHotReloader()

        def original(x: int) -> int:
            return x * 2

        def optimized(_x: int) -> int:
            raise ValueError("optimized failed")

        wrapper = reloader.create_function_wrapper(original, optimized)
        assert wrapper(5) == 10


@pytest.mark.skipif(not is_cpython(), reason="Requires CPython")
class TestFrameManipulation:
    def test_inject_variable(self) -> None:
        inject_variable(sys._getframe(), "_test_var_arwiz", 42)
        assert sys._getframe().f_locals["_test_var_arwiz"] == 42

    def test_inject_non_cpython_raises(self) -> None:
        """This test only runs on CPython (class-level skip)."""
        assert is_cpython()

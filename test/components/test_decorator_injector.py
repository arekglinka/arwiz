"""Tests for arwiz.decorator_injector — AST-based decorator injection."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest
from arwiz.decorator_injector.core import DefaultDecoratorInjector
from arwiz.decorator_injector.import_hook import (
    ArwizImportFinder,
    install_import_hook,
    uninstall_import_hook,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "targets"


@pytest.fixture()
def simple_loop_path() -> Path:
    return FIXTURES_DIR / "simple_loop.py"


@pytest.fixture()
def injector() -> DefaultDecoratorInjector:
    return DefaultDecoratorInjector()


class TestInjectDecorators:
    def test_adds_decorator_to_functions(
        self, injector: DefaultDecoratorInjector, simple_loop_path: Path
    ) -> None:
        tmp_path = injector.inject_decorators(simple_loop_path, decorator_name="test_deco")
        try:
            tree = ast.parse(tmp_path.read_text(encoding="utf-8"))
            decorated = [
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef)
                and any(
                    isinstance(d, ast.Name) and d.id == "test_deco" for d in node.decorator_list
                )
            ]
            assert len(decorated) >= 2
        finally:
            injector.remove_injected(tmp_path)

    def test_custom_decorator_name(
        self, injector: DefaultDecoratorInjector, simple_loop_path: Path
    ) -> None:
        tmp_path = injector.inject_decorators(simple_loop_path, decorator_name="my_custom_dec")
        try:
            content = tmp_path.read_text(encoding="utf-8")
            assert "@my_custom_dec" in content
        finally:
            injector.remove_injected(tmp_path)

    def test_output_is_valid_python(
        self, injector: DefaultDecoratorInjector, simple_loop_path: Path
    ) -> None:
        tmp_path = injector.inject_decorators(simple_loop_path, decorator_name="test_deco")
        try:
            compile(tmp_path.read_text(encoding="utf-8"), str(tmp_path), "exec")
        finally:
            injector.remove_injected(tmp_path)

    def test_original_unchanged(
        self, injector: DefaultDecoratorInjector, simple_loop_path: Path
    ) -> None:
        original = simple_loop_path.read_text(encoding="utf-8")
        tmp_path = injector.inject_decorators(simple_loop_path)
        try:
            pass
        finally:
            injector.remove_injected(tmp_path)
        assert simple_loop_path.read_text(encoding="utf-8") == original


class TestTempFile:
    def test_created(self, injector: DefaultDecoratorInjector, simple_loop_path: Path) -> None:
        tmp_path = injector.inject_decorators(simple_loop_path)
        try:
            assert tmp_path.exists()
        finally:
            injector.remove_injected(tmp_path)

    def test_remove_deletes_file(
        self, injector: DefaultDecoratorInjector, simple_loop_path: Path
    ) -> None:
        tmp_path = injector.inject_decorators(simple_loop_path)
        assert tmp_path.exists()
        injector.remove_injected(tmp_path)
        assert not tmp_path.exists()


class TestInputOverride:
    def test_replaces_args(self, injector: DefaultDecoratorInjector) -> None:
        def sample_func(a: int, b: int) -> int:
            return a + b

        override = injector.create_input_override_decorator({"args": [10, 20]})
        wrapped = override(sample_func)
        assert wrapped(1, 2) == 30

    def test_replaces_kwargs(self, injector: DefaultDecoratorInjector) -> None:
        def sample_func(a: int, b: int) -> int:
            return a * b

        override = injector.create_input_override_decorator({"kwargs": {"a": 5, "b": 6}})
        wrapped = override(sample_func)
        assert wrapped(1, 1) == 30

    def test_no_override_passes_through(self, injector: DefaultDecoratorInjector) -> None:
        def sample_func(a: int) -> int:
            return a

        override = injector.create_input_override_decorator({})
        wrapped = override(sample_func)
        assert wrapped(42) == 42


class TestImportHook:
    def test_install_and_uninstall(self) -> None:
        finder = install_import_hook(target_modules={"nonexistent_test_module"})
        try:
            assert finder in sys.meta_path
        finally:
            uninstall_import_hook(finder)
        assert finder not in sys.meta_path

    def test_finder_returns_none(self) -> None:
        finder = ArwizImportFinder("test_deco", target_modules={"some_module"})
        assert finder.find_spec("some_module") is None
        assert "some_module" in finder.intercepted

    def test_uninstall_nonexistent_no_error(self) -> None:
        finder = ArwizImportFinder("test_deco")
        uninstall_import_hook(finder)  # should not raise

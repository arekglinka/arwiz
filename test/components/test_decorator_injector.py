import ast
from pathlib import Path

import pytest
from arwiz.decorator_injector.core import DefaultDecoratorInjector


@pytest.fixture(scope="module")
def simple_loop_path() -> Path:
    return Path(__file__).parent.parent / "fixtures" / "targets" / "simple_loop.py"


@pytest.fixture(scope="module")
def injector() -> DefaultDecoratorInjector:
    return DefaultDecoratorInjector()


def test_inject_decorators_adds_decorator(injector, simple_loop_path):
    tmp_path = injector.inject_decorators(simple_loop_path, decorator_name="test_deco")
    try:
        injected_content = tmp_path.read_text(encoding="utf-8")
        tree = ast.parse(injected_content)
        decorated_funcs = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and any(isinstance(d, ast.Name) and d.id == "test_deco" for d in node.decorator_list)
        ]
        assert len(decorated_funcs) >= 2  # compute_sum and main
    finally:
        injector.remove_injected(tmp_path)


def test_injected_output_valid_python(injector, simple_loop_path):
    tmp_path = injector.inject_decorators(simple_loop_path, decorator_name="test_deco")
    try:
        injected_content = tmp_path.read_text(encoding="utf-8")
        compile(injected_content, str(tmp_path), "exec")
    finally:
        injector.remove_injected(tmp_path)


def test_original_file_unchanged(injector, simple_loop_path):
    original_content = simple_loop_path.read_text(encoding="utf-8")
    tmp_path = injector.inject_decorators(simple_loop_path, decorator_name="test_deco")
    try:
        pass
    finally:
        injector.remove_injected(tmp_path)
    assert simple_loop_path.read_text(encoding="utf-8") == original_content


def test_temp_file_created(injector, simple_loop_path):
    tmp_path = injector.inject_decorators(simple_loop_path, decorator_name="test_deco")
    try:
        assert tmp_path.exists()
    finally:
        injector.remove_injected(tmp_path)


def test_remove_injected_deletes_file(injector, simple_loop_path):
    tmp_path = injector.inject_decorators(simple_loop_path, decorator_name="test_deco")
    assert tmp_path.exists()
    injector.remove_injected(tmp_path)
    assert not tmp_path.exists()


def test_create_input_override_replaces_args(injector):
    def sample_func(a, b):
        return a + b

    override = injector.create_input_override_decorator({"args": [10, 20]})
    wrapped = override(sample_func)
    result = wrapped(1, 2)
    assert result == 30

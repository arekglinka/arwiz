"""Default implementation of decorator injection."""

from __future__ import annotations

import ast
import functools
import os
import tempfile
from collections.abc import Callable
from pathlib import Path

from arwiz.decorator_injector.interface import DecoratorInjectorProtocol


class _DecoratorInjector(ast.NodeTransformer):
    def __init__(self, decorator_name: str) -> None:
        self.decorator_name = decorator_name

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        self.generic_visit(node)
        already_has = any(
            d
            for d in node.decorator_list
            if isinstance(d, ast.Name) and d.id == self.decorator_name
        )
        if already_has:
            return node
        decorator = ast.Name(id=self.decorator_name, ctx=ast.Load())
        node.decorator_list.insert(0, decorator)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        self.generic_visit(node)
        already_has = any(
            d
            for d in node.decorator_list
            if isinstance(d, ast.Name) and d.id == self.decorator_name
        )
        if already_has:
            return node
        decorator = ast.Name(id=self.decorator_name, ctx=ast.Load())
        node.decorator_list.insert(0, decorator)
        return node


class DefaultDecoratorInjector(DecoratorInjectorProtocol):
    def inject_decorators(
        self,
        source_path: Path | str,
        decorator_name: str = "arwiz_capture",
    ) -> Path:
        source_path = Path(source_path)
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(source_path))
        transformer = _DecoratorInjector(decorator_name)
        modified_tree = transformer.visit(tree)
        ast.fix_missing_locations(modified_tree)

        tmp_dir = tempfile.mkdtemp(prefix="arwiz_inject_")
        tmp_path = Path(tmp_dir) / source_path.name
        tmp_path.write_text(ast.unparse(modified_tree), encoding="utf-8")
        return tmp_path

    def create_input_override_decorator(self, input_data: dict) -> Callable:
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if "args" in input_data and "kwargs" in input_data:
                    return func(*input_data["args"], **input_data["kwargs"])
                if "args" in input_data:
                    return func(*input_data["args"])
                if "kwargs" in input_data:
                    return func(**input_data["kwargs"])
                return func(*args, **kwargs)

            return wrapper

        return decorator

    def remove_injected(self, temp_path: Path) -> None:
        if temp_path.exists():
            os.unlink(temp_path)
            parent = temp_path.parent
            if parent.exists() and not any(parent.iterdir()):
                parent.rmdir()

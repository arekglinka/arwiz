"""Default implementation of hot function reloading."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from pathlib import Path

from arwiz.hot_reload.interface import HotReloadProtocol


class DefaultHotReloader(HotReloadProtocol):
    _originals: dict[str, Callable] = {}

    def reload_function(
        self,
        module_path: Path | str,
        function_name: str,
        new_source: str,
    ) -> bool:
        try:
            compiled_code = compile(new_source, "<string>", "exec")
        except SyntaxError:
            return False

        new_ns: dict = {}
        try:
            exec(compiled_code, new_ns)  # noqa: S102
        except Exception:
            return False

        new_func = new_ns.get(function_name)
        if new_func is None or not callable(new_func):
            return False

        module_path = Path(module_path)
        module_name = module_path.stem
        key = f"{module_name}.{function_name}"

        if key not in self._originals:
            try:
                module = importlib.import_module(module_name)
                original_func = getattr(module, function_name)
                self._originals[key] = original_func
            except (ImportError, AttributeError):
                self._originals[key] = new_func

        try:
            module = importlib.import_module(module_name)
            setattr(module, function_name, new_func)
            return True
        except ImportError:
            return False

    def create_function_wrapper(
        self,
        original: Callable,
        optimized: Callable,
    ) -> Callable:
        def wrapper(*args, **kwargs):
            try:
                return optimized(*args, **kwargs)
            except Exception:
                return original(*args, **kwargs)

        wrapper.__name__ = f"wrapped_{original.__name__}"
        return wrapper

    def rollback(
        self,
        module_path: Path | str,
        function_name: str,
    ) -> None:
        module_path = Path(module_path)
        module_name = module_path.stem
        key = f"{module_name}.{function_name}"

        if key not in self._originals:
            return

        original = self._originals[key]
        try:
            module = importlib.import_module(module_name)
            setattr(module, function_name, original)
        except ImportError:
            pass

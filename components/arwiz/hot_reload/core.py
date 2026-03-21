"""Default implementation of hot function reloading."""

from __future__ import annotations

import functools
import importlib
import warnings
from collections.abc import Callable
from pathlib import Path

from arwiz.hot_reload.interface import HotReloadProtocol


class DefaultHotReloader(HotReloadProtocol):
    def __init__(self) -> None:
        self._originals: dict[str, Callable] = {}

    def reload_function(
        self,
        module_path: Path | str,
        function_name: str,
        new_source: str,
    ) -> bool:
        try:
            compiled_code = compile(new_source, "<arwiz-reload>", "exec")
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
        key = f"{module_name}:{function_name}"

        try:
            module = importlib.import_module(module_name)
        except ImportError:
            return False

        if key not in self._originals:
            try:
                self._originals[key] = getattr(module, function_name)
            except AttributeError:
                return False

        setattr(module, function_name, new_func)
        return True

    def create_function_wrapper(
        self,
        original: Callable,
        optimized: Callable,
    ) -> Callable:
        @functools.wraps(original)
        def wrapper(*args: object, **kwargs: object) -> object:
            try:
                return optimized(*args, **kwargs)
            except Exception:
                warnings.warn(
                    f"[arwiz] Optimized {original.__name__} failed, falling back to original",
                    stacklevel=2,
                )
                return original(*args, **kwargs)

        return wrapper

    def rollback(
        self,
        module_path: Path | str,
        function_name: str,
    ) -> None:
        module_path = Path(module_path)
        module_name = module_path.stem
        key = f"{module_name}:{function_name}"

        if key not in self._originals:
            raise KeyError(f"No original stored for {key}")

        original = self._originals.pop(key)
        module = importlib.import_module(module_name)
        setattr(module, function_name, original)

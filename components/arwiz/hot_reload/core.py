"""Default implementation of hot function reloading."""

from __future__ import annotations

import functools
import importlib
import sys
import warnings
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

from arwiz.hot_reload.interface import HotReloadProtocol  # pyrefly: ignore[missing-import]


class DefaultHotReloader(HotReloadProtocol):
    def __init__(self) -> None:
        self._originals: dict[str, Callable] = {}

    def reload_function(
        self,
        module_path: Path | str,
        function_name: str,
        new_source: str,
        module: ModuleType | None = None,
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

        target_module = self._resolve_module(Path(module_path), module)
        if target_module is None:
            return False

        module_name = target_module.__name__
        key = f"{module_name}:{function_name}"

        try:
            original_func = getattr(target_module, function_name)
        except AttributeError:
            return False

        if key not in self._originals:
            self._originals[key] = original_func

        new_func.__module__ = original_func.__module__
        new_func.__qualname__ = original_func.__qualname__
        new_func.__annotations__ = getattr(original_func, "__annotations__", {})

        setattr(target_module, function_name, new_func)
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
        module = self._resolve_module(module_path)
        if module is None:
            raise ImportError(f"Could not resolve module for {module_path}")

        module_name = module.__name__
        key = f"{module_name}:{function_name}"

        if key not in self._originals:
            raise KeyError(f"No original stored for {key}")

        original = self._originals.pop(key)
        setattr(module, function_name, original)

    def clear_originals(self) -> int:
        """Remove all stored originals.

        Call after a profiling session to free memory. Does NOT restore
        the original functions — use rollback() first if restoration is needed.

        Returns:
            Number of entries cleared.
        """
        count = len(self._originals)
        self._originals.clear()
        return count

    def _resolve_module(
        self,
        module_path: Path,
        module: ModuleType | None = None,
    ) -> ModuleType | None:
        if module is not None:
            return module

        module_path_resolved = module_path.resolve()

        main_module = sys.modules.get("__main__")
        main_file = getattr(main_module, "__file__", None) if main_module is not None else None
        if main_file and Path(main_file).resolve() == module_path_resolved:
            return main_module

        for candidate in sys.modules.values():
            candidate_file = getattr(candidate, "__file__", None)
            if candidate_file is None:
                continue
            if Path(candidate_file).resolve() == module_path_resolved:
                return candidate

        module_name = module_path.stem
        try:
            return sys.modules[module_name]
        except KeyError:
            try:
                return importlib.import_module(module_name)
            except ImportError:
                return None

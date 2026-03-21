"""Protocol interface for hot function reloading."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class HotReloadProtocol(Protocol):
    """Protocol defining the hot reload interface."""

    def reload_function(
        self,
        module_path: Path | str,
        function_name: str,
        new_source: str,
    ) -> bool: ...

    def create_function_wrapper(
        self,
        original: Callable,
        optimized: Callable,
    ) -> Callable: ...

    def rollback(
        self,
        module_path: Path | str,
        function_name: str,
    ) -> None: ...

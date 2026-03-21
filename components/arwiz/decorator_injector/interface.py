"""Protocol interface for decorator injection."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class DecoratorInjectorProtocol(Protocol):
    """Protocol defining the decorator injector interface."""

    def inject_decorators(
        self,
        source_path: Path | str,
        decorator_name: str = "arwiz_capture",
    ) -> Path: ...

    def create_input_override_decorator(self, input_data: dict) -> Callable: ...

    def remove_injected(self, temp_path: Path) -> None: ...

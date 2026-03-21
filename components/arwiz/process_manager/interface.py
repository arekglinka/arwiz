"""Protocol interface for process management."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from arwiz.process_manager.core import ProcessResult


@runtime_checkable
class ProcessManagerProtocol(Protocol):
    """Protocol defining the process manager interface."""

    def run_script(
        self,
        script_path: Path | str,
        args: list[str] | None = None,
        timeout_seconds: int = 300,
        memory_limit_mb: int | None = None,
    ) -> ProcessResult: ...

    def kill_process(self, pid: int) -> None: ...

    def get_memory_usage_mb(self, pid: int) -> float: ...

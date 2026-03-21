"""Protocol interface for coverage tracing."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from arwiz.foundation import BranchCoverage


@runtime_checkable
class CoverageTracerProtocol(Protocol):
    """Protocol defining the coverage tracer interface."""

    def trace_branches(
        self,
        script_path: Path | str,
        args: list[str] | None = None,
    ) -> BranchCoverage: ...

    def get_uncovered_branches(
        self,
        coverage: BranchCoverage,
    ) -> list[tuple[str, int]]: ...

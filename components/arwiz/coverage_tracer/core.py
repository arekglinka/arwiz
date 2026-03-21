"""Default implementation of coverage tracing."""

from __future__ import annotations

import contextlib
import tempfile
import time
from pathlib import Path

from arwiz.coverage_tracer.ast_analyzer import get_static_branches
from arwiz.coverage_tracer.interface import CoverageTracerProtocol
from arwiz.foundation import BranchCoverage, BranchInfo
from arwiz.process_manager import DefaultProcessManager

_TRACE_WRAPPER_TEMPLATE = """\
import sys
import json
import runpy

executed_lines = set()

def tracer(frame, event, arg):
    if event == 'line':
        executed_lines.add(frame.f_lineno)
    return tracer

sys.settrace(tracer)
try:
    runpy.run_path({target_path!r}, run_name="__main__")
except SystemExit:
    pass
sys.settrace(None)

# Output traced lines as JSON to stdout
print("__TRACE_SEPARATOR__")
print(json.dumps(sorted(executed_lines)))
"""


class DefaultCoverageTracer(CoverageTracerProtocol):
    """Traces branch coverage by combining static AST analysis with runtime tracing."""

    def __init__(self) -> None:
        self._process_manager = DefaultProcessManager()

    def trace_branches(
        self,
        script_path: Path | str,
        args: list[str] | None = None,
    ) -> BranchCoverage:
        """Trace branches via AST analysis + runtime line tracing in subprocess."""
        script_path = Path(script_path)
        start = time.perf_counter()

        static_branches = get_static_branches(script_path)
        wrapper_source = _TRACE_WRAPPER_TEMPLATE.format(target_path=str(script_path))
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            prefix="arwiz_trace_",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(wrapper_source)
            wrapper_path = f.name

        try:
            result = self._process_manager.run_script(
                wrapper_path,
                args=args,
                timeout_seconds=30,
            )
        finally:
            with contextlib.suppress(OSError):
                Path(wrapper_path).unlink(missing_ok=True)

        traced_lines: set[int] = set()
        if result.exit_code == 0 and "__TRACE_SEPARATOR__" in result.stdout:
            parts = result.stdout.split("__TRACE_SEPARATOR__")
            if len(parts) >= 2:
                import json

                with contextlib.suppress(json.JSONDecodeError, ValueError):
                    traced_lines = set(json.loads(parts[1].strip()))

        branch_details: list[BranchInfo] = []
        covered_count = 0
        uncovered_line_numbers: list[int] = []

        for branch in static_branches:
            is_taken = branch["line"] in traced_lines
            if is_taken:
                covered_count += 1
            else:
                uncovered_line_numbers.append(branch["line"])

            branch_details.append(
                BranchInfo(
                    line_number=branch["line"],
                    branch_type=branch["type"],
                    condition=branch["condition"],
                    taken=is_taken,
                )
            )

        total = len(static_branches)
        coverage_percent = (covered_count / total * 100) if total > 0 else 0.0

        elapsed_ms = (time.perf_counter() - start) * 1000

        return BranchCoverage(
            total_branches=total,
            covered_branches=covered_count,
            coverage_percent=round(coverage_percent, 2),
            uncovered_lines=uncovered_line_numbers,
            branch_details=branch_details,
            script_path=str(script_path),
            duration_ms=round(elapsed_ms, 2),
        )

    def get_uncovered_branches(
        self,
        coverage: BranchCoverage,
    ) -> list[tuple[str, int]]:
        return [(coverage.script_path, line) for line in coverage.uncovered_lines]

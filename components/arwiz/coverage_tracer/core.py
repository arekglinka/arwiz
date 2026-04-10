"""Default implementation of coverage tracing.

Combines static AST analysis with runtime tracing via sys.settrace
to measure branch coverage of Python scripts.
"""

from __future__ import annotations

import contextlib
import json
import tempfile
import time
from pathlib import Path

from arwiz.coverage_tracer.ast_analyzer import get_static_branches
from arwiz.coverage_tracer.interface import CoverageTracerProtocol
from arwiz.foundation import BranchCoverage, BranchInfo
from arwiz.process_manager import DefaultProcessManager

_TRACE_WRAPPER = """\
import os
import sys
import json
import runpy

_executed = set()

def _tracer(frame, event, arg):
    if event == 'line':
        _executed.add(frame.f_lineno)
    return _tracer

sys.settrace(_tracer)
sys.path.insert(0, os.getcwd())
sys.argv = [{target_path!r}] + sys.argv[1:]
try:
    runpy.run_path({target_path!r}, run_name="__main__")
except SystemExit:
    pass
sys.settrace(None)

print("__ARWIZ_TRACE_SEP__", file=sys.stderr)
print(json.dumps(sorted(_executed)), file=sys.stderr)
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

        if script_path.suffix != ".py":
            return BranchCoverage(
                total_branches=0,
                covered_branches=0,
                coverage_percent=100.0,
                uncovered_lines=[],
                branch_details=[],
                script_path=str(script_path),
                duration_ms=0.0,
            )

        static_branches = get_static_branches(script_path)
        wrapper_source = _TRACE_WRAPPER.format(target_path=str(script_path))

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
        if "__ARWIZ_TRACE_SEP__" in result.stderr:
            parts = result.stderr.split("__ARWIZ_TRACE_SEP__")
            if len(parts) >= 2:
                with contextlib.suppress(json.JSONDecodeError, ValueError):
                    traced_lines = set(json.loads(parts[1].strip()))

        branch_details: list[BranchInfo] = []
        covered_count = 0
        uncovered_line_numbers: list[int] = []

        for line_num, branch_type in static_branches:
            taken = line_num in traced_lines
            if taken:
                covered_count += 1
            else:
                uncovered_line_numbers.append(line_num)

            branch_details.append(
                BranchInfo(
                    line_number=line_num,
                    branch_type=branch_type,
                    condition="",
                    taken=taken,
                )
            )

        total = len(static_branches)
        coverage_pct = (covered_count / total * 100) if total > 0 else 0.0
        elapsed_ms = (time.perf_counter() - start) * 1000

        return BranchCoverage(
            total_branches=total,
            covered_branches=covered_count,
            coverage_percent=round(coverage_pct, 2),
            uncovered_lines=uncovered_line_numbers,
            branch_details=branch_details,
            script_path=str(script_path),
            duration_ms=round(elapsed_ms, 2),
        )

    def get_uncovered_branches(
        self,
        coverage: BranchCoverage,
    ) -> list[tuple[str, int]]:
        """Get uncovered branches as (branch_type, line_number) tuples."""
        return [(bi.branch_type, bi.line_number) for bi in coverage.branch_details if not bi.taken]

from pathlib import Path

import pytest
from arwiz.coverage_tracer.ast_analyzer import get_static_branches
from arwiz.coverage_tracer.core import DefaultCoverageTracer


@pytest.fixture(scope="module")
def branching_path() -> Path:
    return Path(__file__).parent.parent / "fixtures" / "targets" / "branching.py"


@pytest.fixture(scope="module")
def simple_loop_path() -> Path:
    return Path(__file__).parent.parent / "fixtures" / "targets" / "simple_loop.py"


def test_ast_analyzer_finds_branches(branching_path):
    branches = get_static_branches(branching_path)
    assert len(branches) >= 3
    branch_types = {b["type"] for b in branches}
    assert "If" in branch_types


def test_ast_analyzer_finds_loops(branching_path):
    branches = get_static_branches(branching_path)
    loop_branches = [b for b in branches if b["type"] == "For"]
    assert len(loop_branches) >= 1
    for branch in loop_branches:
        assert "line" in branch
        assert "condition" in branch


def test_trace_branches_returns_coverage(branching_path):
    tracer = DefaultCoverageTracer()
    coverage = tracer.trace_branches(branching_path)
    assert coverage.total_branches > 0
    assert coverage.coverage_percent > 0
    assert coverage.coverage_percent <= 100
    assert coverage.script_path == str(branching_path)


def test_get_uncovered_branches():
    tracer = DefaultCoverageTracer()
    from arwiz.foundation import BranchCoverage

    fake_coverage = BranchCoverage(
        total_branches=5,
        covered_branches=3,
        coverage_percent=60.0,
        uncovered_lines=[10, 20],
        branch_details=[],
        script_path="/tmp/test.py",
        duration_ms=1.0,
    )
    uncovered = tracer.get_uncovered_branches(fake_coverage)
    assert len(uncovered) == 2
    assert uncovered[0] == ("/tmp/test.py", 10)
    assert uncovered[1] == ("/tmp/test.py", 20)


def test_injected_output_valid_python(branching_path):
    branches = get_static_branches(branching_path)
    for branch in branches:
        assert isinstance(branch["line"], int)
        assert isinstance(branch["type"], str)
        assert isinstance(branch["condition"], str)

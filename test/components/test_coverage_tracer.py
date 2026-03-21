"""Tests for arwiz.coverage_tracer — AST analysis + runtime branch tracing."""

from __future__ import annotations

from pathlib import Path

import pytest
from arwiz.coverage_tracer.ast_analyzer import get_static_branches
from arwiz.coverage_tracer.core import DefaultCoverageTracer
from arwiz.foundation import BranchCoverage, BranchInfo

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "targets"


@pytest.fixture(scope="module")
def branching_path() -> Path:
    return FIXTURES_DIR / "branching.py"


class TestASTAnalyzer:
    def test_finds_if_branches(self, branching_path: Path) -> None:
        branches = get_static_branches(branching_path)
        branch_types = {btype for _, btype in branches}
        assert "if" in branch_types

    def test_finds_elif_branches(self, branching_path: Path) -> None:
        branches = get_static_branches(branching_path)
        branch_types = {btype for _, btype in branches}
        assert "elif" in branch_types

    def test_finds_else_branches(self, branching_path: Path) -> None:
        branches = get_static_branches(branching_path)
        branch_types = {btype for _, btype in branches}
        assert "else" in branch_types

    def test_finds_for_loops(self, branching_path: Path) -> None:
        branches = get_static_branches(branching_path)
        for_branches = [(line, btype) for line, btype in branches if btype == "for"]
        assert len(for_branches) >= 1

    def test_returns_tuples(self, branching_path: Path) -> None:
        branches = get_static_branches(branching_path)
        for branch in branches:
            assert isinstance(branch, tuple)
            assert len(branch) == 2
            assert isinstance(branch[0], int)
            assert isinstance(branch[1], str)


class TestTraceBranches:
    def test_returns_coverage(self, branching_path: Path) -> None:
        tracer = DefaultCoverageTracer()
        coverage = tracer.trace_branches(branching_path)
        assert coverage.total_branches > 0
        assert coverage.coverage_percent >= 0
        assert coverage.coverage_percent <= 100
        assert coverage.script_path == str(branching_path)

    def test_coverage_percent_positive(self, branching_path: Path) -> None:
        tracer = DefaultCoverageTracer()
        coverage = tracer.trace_branches(branching_path)
        assert coverage.coverage_percent > 0

    def test_branch_details_populated(self, branching_path: Path) -> None:
        tracer = DefaultCoverageTracer()
        coverage = tracer.trace_branches(branching_path)
        for bi in coverage.branch_details:
            assert isinstance(bi, BranchInfo)
            assert isinstance(bi.line_number, int)
            assert isinstance(bi.branch_type, str)


class TestGetUncoveredBranches:
    def test_returns_uncovered(self) -> None:
        tracer = DefaultCoverageTracer()
        fake = BranchCoverage(
            total_branches=3,
            covered_branches=1,
            coverage_percent=33.33,
            uncovered_lines=[20, 30],
            branch_details=[
                BranchInfo(line_number=10, branch_type="if", condition="", taken=True),
                BranchInfo(line_number=20, branch_type="elif", condition="", taken=False),
                BranchInfo(line_number=30, branch_type="else", condition="", taken=False),
            ],
            script_path="/tmp/test.py",
            duration_ms=1.0,
        )
        uncovered = tracer.get_uncovered_branches(fake)
        assert len(uncovered) == 2
        assert ("elif", 20) in uncovered
        assert ("else", 30) in uncovered

    def test_empty_when_all_covered(self) -> None:
        tracer = DefaultCoverageTracer()
        fake = BranchCoverage(
            total_branches=1,
            covered_branches=1,
            coverage_percent=100.0,
            uncovered_lines=[],
            branch_details=[
                BranchInfo(line_number=10, branch_type="if", condition="", taken=True),
            ],
            script_path="/tmp/test.py",
            duration_ms=1.0,
        )
        assert tracer.get_uncovered_branches(fake) == []


class TestEdgeCases:
    def test_try_except_detection(self, tmp_path: Path) -> None:
        script = tmp_path / "try_except.py"
        script.write_text(
            "try:\n"
            "    x = 1\n"
            "except ValueError:\n"
            "    x = 2\n"
            "except Exception:\n"
            "    x = 3\n"
            "finally:\n"
            "    x = 4\n"
        )
        branches = get_static_branches(script)
        branch_types = {bt for _, bt in branches}
        assert "try" in branch_types
        assert "except" in branch_types
        assert "finally" in branch_types

    def test_while_loop_detection(self, tmp_path: Path) -> None:
        script = tmp_path / "while_loop.py"
        script.write_text("x = 0\nwhile x < 10:\n    x += 1\n")
        branches = get_static_branches(script)
        branch_types = {bt for _, bt in branches}
        assert "while" in branch_types
        assert len(branches) >= 1

    def test_deeply_nested_if_elif_else(self, tmp_path: Path) -> None:
        script = tmp_path / "nested.py"
        script.write_text(
            "if True:\n"
            "    if False:\n"
            "        pass\n"
            "    elif True:\n"
            "        if None:\n"
            "            pass\n"
            "        else:\n"
            "            pass\n"
            "    else:\n"
            "        pass\n"
            "else:\n"
            "    pass\n"
        )
        branches = get_static_branches(script)
        branch_types = {bt for _, bt in branches}
        assert "if" in branch_types
        assert "elif" in branch_types
        assert "else" in branch_types
        assert len(branches) >= 5

    def test_no_branches_plain_assignments(self, tmp_path: Path) -> None:
        script = tmp_path / "plain.py"
        script.write_text("x = 1\ny = 2\nz = x + y\n")
        branches = get_static_branches(script)
        assert branches == []

    def test_nonexistent_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            get_static_branches(tmp_path / "does_not_exist.py")

    def test_invalid_syntax_raises(self, tmp_path: Path) -> None:
        script = tmp_path / "bad_syntax.py"
        script.write_text("def foo(\n")
        with pytest.raises(SyntaxError):
            get_static_branches(script)

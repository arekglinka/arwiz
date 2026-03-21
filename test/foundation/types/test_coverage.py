"""Tests for arwiz.foundation.types.coverage models."""

from arwiz.foundation.types.coverage import BranchCoverage, BranchInfo, InputSnapshot


class TestInputSnapshot:
    def test_create_minimal(self):
        snap = InputSnapshot(
            snapshot_id="snap_001",
            function_name="process",
            args_repr="[1, 2, 3]",
            kwargs_repr="{}",
            timestamp="2025-01-01T00:00:00Z",
            content_hash="abc123",
        )
        assert snap.snapshot_id == "snap_001"
        assert snap.function_name == "process"
        assert snap.args_repr == "[1, 2, 3]"
        assert snap.kwargs_repr == "{}"
        assert snap.result_repr is None
        assert snap.storage_path is None

    def test_full_snapshot(self):
        snap = InputSnapshot(
            snapshot_id="snap_002",
            function_name="calc",
            args_repr="(10,)",
            kwargs_repr="{'n': 5}",
            result_repr="50",
            timestamp="2025-01-01T00:00:00Z",
            content_hash="def456",
            storage_path=".arwiz/inputs/snap_002.json",
        )
        assert snap.result_repr == "50"
        assert snap.storage_path == ".arwiz/inputs/snap_002.json"


class TestBranchInfo:
    def test_create_with_defaults(self):
        branch = BranchInfo(
            line_number=10,
            branch_type="if",
            condition="x > 0",
        )
        assert branch.line_number == 10
        assert branch.branch_type == "if"
        assert branch.condition == "x > 0"
        assert branch.taken is False

    def test_taken_branch(self):
        branch = BranchInfo(
            line_number=20,
            branch_type="elif",
            condition="x == 0",
            taken=True,
        )
        assert branch.taken is True

    def test_all_branch_types(self):
        for btype in ["if", "elif", "else", "for", "while", "try", "except"]:
            b = BranchInfo(line_number=1, branch_type=btype, condition="True")
            assert b.branch_type == btype


class TestBranchCoverage:
    def test_create_minimal(self):
        cov = BranchCoverage(
            total_branches=10,
            covered_branches=7,
            coverage_percent=70.0,
            script_path="run.py",
            duration_ms=50.0,
        )
        assert cov.total_branches == 10
        assert cov.covered_branches == 7
        assert cov.coverage_percent == 70.0
        assert cov.uncovered_lines == []
        assert cov.branch_details == []

    def test_full_coverage(self):
        branches = [
            BranchInfo(line_number=5, branch_type="if", condition="x>0", taken=True),
            BranchInfo(line_number=8, branch_type="elif", condition="x==0", taken=False),
            BranchInfo(line_number=10, branch_type="for", condition="range(n)", taken=True),
        ]
        cov = BranchCoverage(
            total_branches=3,
            covered_branches=2,
            coverage_percent=66.67,
            uncovered_lines=[8],
            branch_details=branches,
            script_path="main.py",
            duration_ms=100.0,
        )
        assert len(cov.branch_details) == 3
        assert cov.uncovered_lines == [8]
        assert cov.branch_details[1].taken is False
        assert cov.branch_details[2].taken is True

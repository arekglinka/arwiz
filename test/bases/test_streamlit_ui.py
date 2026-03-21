"""Unit tests for streamlit_ui components.

Tests focus on component functions that don't require Streamlit runtime.
"""

from __future__ import annotations

from arwiz.foundation import (
    CallNode,
    HotSpot,
    OptimizationAttempt,
)
from arwiz.streamlit_ui.components.code_diff import (
    compute_line_diff,
    format_code_for_display,
    get_diff_stats,
)
from arwiz.streamlit_ui.components.flame_graph import (
    _truncate_label,
    build_call_tree_table,
    build_flame_graph,
    build_hotspots_table,
)
from arwiz.streamlit_ui.components.metrics_display import (
    build_metrics_display,
    build_timing_display,
    format_equivalence_result,
    format_speedup,
    get_speedup_color,
)
from arwiz.streamlit_ui.state import SessionState


class TestSessionState:
    def test_init_defaults(self) -> None:
        state = SessionState()
        assert state.profile_result is None
        assert state.hotspots == []
        assert state.coverage is None
        assert state.optimization_attempt is None
        assert state.selected_hotspot_idx == 0
        assert state.original_code == ""
        assert state.optimized_code == ""

    def test_clear_resets_state(self) -> None:
        state = SessionState()
        state.original_code = "some code"
        state.selected_hotspot_idx = 5
        state.hotspots = [
            HotSpot(
                function_name="test",
                file_path="test.py",
                line_range=(1, 10),
                cumulative_time_ms=100.0,
                self_time_ms=50.0,
            )
        ]

        state.clear()

        assert state.profile_result is None
        assert state.hotspots == []
        assert state.selected_hotspot_idx == 0
        assert state.original_code == ""


class TestFlameGraphComponents:
    def test_build_flame_graph_empty_tree(self) -> None:
        fig = build_flame_graph(None, 100.0)
        assert fig is not None
        assert len(fig.data) == 0 or len(fig.layout.annotations) > 0

    def test_build_flame_graph_with_tree(self) -> None:
        tree = CallNode(
            function_name="main",
            file_path="test.py",
            line_number=1,
            cumulative_time_ms=100.0,
            self_time_ms=10.0,
            call_count=1,
            children=[
                CallNode(
                    function_name="helper",
                    file_path="test.py",
                    line_number=5,
                    cumulative_time_ms=50.0,
                    self_time_ms=40.0,
                    call_count=2,
                )
            ],
        )
        fig = build_flame_graph(tree, 100.0)
        assert fig is not None
        assert len(fig.data) == 1

    def test_build_call_tree_table_empty(self) -> None:
        rows = build_call_tree_table(None)
        assert rows == []

    def test_build_call_tree_table_with_tree(self) -> None:
        tree = CallNode(
            function_name="main",
            file_path="test.py",
            line_number=1,
            cumulative_time_ms=100.0,
            self_time_ms=10.0,
            call_count=1,
            children=[
                CallNode(
                    function_name="helper",
                    file_path="test.py",
                    line_number=5,
                    cumulative_time_ms=50.0,
                    self_time_ms=40.0,
                    call_count=2,
                )
            ],
        )
        rows = build_call_tree_table(tree)
        assert len(rows) == 2
        assert rows[0]["function"] == "main"
        assert rows[1]["function"] == "  helper"

    def test_build_hotspots_table(self) -> None:
        hotspots = [
            HotSpot(
                function_name="slow_func",
                file_path="test.py",
                line_range=(10, 20),
                cumulative_time_ms=200.0,
                self_time_ms=150.0,
                call_count=5,
                potential_speedup=45.0,
            )
        ]
        rows = build_hotspots_table(hotspots)
        assert len(rows) == 1
        assert rows[0]["function"] == "slow_func"
        assert rows[0]["potential_speedup"] == "45.0%"

    def test_truncate_label_short(self) -> None:
        assert _truncate_label("short") == "short"

    def test_truncate_label_long(self) -> None:
        long_name = "a_very_long_function_name_that_exceeds_limit"
        result = _truncate_label(long_name, max_len=20)
        assert len(result) == 20
        assert result.endswith("...")


class TestCodeDiffComponents:
    def test_format_code_for_display_empty(self) -> None:
        result = format_code_for_display("")
        assert result == ""

    def test_format_code_for_display_simple(self) -> None:
        code = "def foo():\n    pass\n"
        result = format_code_for_display(code)
        assert "def foo():" in result

    def test_format_code_for_display_truncation(self) -> None:
        lines = ["line " + str(i) for i in range(150)]
        code = "\n".join(lines)
        result = format_code_for_display(code, max_lines=100)
        assert "more lines" in result

    def test_compute_line_diff_identical(self) -> None:
        orig, opt = compute_line_diff("a\nb\nc", "a\nb\nc")
        assert len(orig) == 3
        assert len(opt) == 3
        for line in orig:
            assert line[2] == "unchanged"

    def test_compute_line_diff_added(self) -> None:
        orig, opt = compute_line_diff("a\nb", "a\nb\nc")
        assert len(opt) == 3
        assert opt[2][2] == "added"

    def test_compute_line_diff_removed(self) -> None:
        orig, opt = compute_line_diff("a\nb\nc", "a\nb")
        assert len(orig) == 3
        assert orig[2][2] == "removed"

    def test_get_diff_stats(self) -> None:
        orig = "a\nb\nc"
        opt = "a\nb"
        stats = get_diff_stats(orig, opt)
        assert stats["original_lines"] == 3
        assert stats["optimized_lines"] == 2
        assert stats["line_delta"] == -1


class TestMetricsDisplay:
    def test_format_speedup_positive(self) -> None:
        assert format_speedup(50.0) == "+50.0%"
        assert format_speedup(0.5) == "+0.5%"

    def test_format_speedup_zero(self) -> None:
        assert format_speedup(0.0) == "0.0%"

    def test_format_speedup_negative(self) -> None:
        assert format_speedup(-10.0) == "-10.0%"

    def test_get_speedup_color_high(self) -> None:
        assert get_speedup_color(60.0) == "green"
        assert get_speedup_color(50.0) == "green"

    def test_get_speedup_color_medium(self) -> None:
        assert get_speedup_color(30.0) == "lightgreen"

    def test_get_speedup_color_low(self) -> None:
        assert get_speedup_color(10.0) == "gray"
        assert get_speedup_color(0.0) == "gray"

    def test_get_speedup_color_negative(self) -> None:
        assert get_speedup_color(-10.0) == "red"

    def test_format_equivalence_result_passed(self) -> None:
        result = format_equivalence_result(True, None)
        assert result["status"] == "PASSED"
        assert result["color"] == "green"

    def test_format_equivalence_result_failed(self) -> None:
        result = format_equivalence_result(False, "Values differ")
        assert result["status"] == "FAILED"
        assert result["color"] == "red"
        assert "differ" in result["message"]

    def test_build_metrics_display_none(self) -> None:
        metrics = build_metrics_display(None)
        assert metrics["speedup"] == "N/A"
        assert metrics["syntax_valid"] is None

    def test_build_metrics_display_with_attempt(self) -> None:
        attempt = OptimizationAttempt(
            attempt_id="test_123",
            original_code="def foo(): pass",
            optimized_code="def foo(): return 1",
            strategy="llm_generated",
            llm_model="gpt-4",
            syntax_valid=True,
            passed_equivalence=True,
            speedup_percent=60.0,
        )
        metrics = build_metrics_display(attempt)
        assert metrics["speedup"] == "+60.0%"
        assert metrics["speedup_color"] == "green"
        assert metrics["syntax_valid"] is True
        assert metrics["equivalence"]["status"] == "PASSED"

    def test_build_timing_display_ms(self) -> None:
        timing = build_timing_display(500.0)
        assert timing["value"] == "500.00ms"

    def test_build_timing_display_seconds(self) -> None:
        timing = build_timing_display(5000.0)
        assert timing["value"] == "5.00s"

    def test_build_timing_display_minutes(self) -> None:
        timing = build_timing_display(120000.0)
        assert timing["value"] == "2.00m"

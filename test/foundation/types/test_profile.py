"""Tests for arwiz.foundation.types.profile models."""

from arwiz.foundation.types.profile import CallNode, HotSpot, ProfileResult


class TestCallNode:
    def test_create_with_required_fields(self):
        node = CallNode(function_name="foo", file_path="foo.py", line_number=10)
        assert node.function_name == "foo"
        assert node.file_path == "foo.py"
        assert node.line_number == 10

    def test_defaults(self):
        node = CallNode(function_name="bar", file_path="bar.py", line_number=1)
        assert node.children == []
        assert node.cumulative_time_ms == 0.0
        assert node.self_time_ms == 0.0
        assert node.call_count == 0

    def test_nested_children(self):
        child = CallNode(function_name="child", file_path="c.py", line_number=5)
        parent = CallNode(
            function_name="parent",
            file_path="p.py",
            line_number=1,
            children=[child],
            cumulative_time_ms=100.0,
            self_time_ms=20.0,
            call_count=10,
        )
        assert len(parent.children) == 1
        assert parent.children[0].function_name == "child"
        assert parent.cumulative_time_ms == 100.0

    def test_model_serialization(self):
        node = CallNode(function_name="f", file_path="f.py", line_number=1)
        d = node.model_dump()
        assert "function_name" in d
        assert "children" in d
        assert d["call_count"] == 0


class TestHotSpot:
    def test_create_with_required_fields(self):
        hs = HotSpot(
            function_name="slow_func",
            file_path="slow.py",
            line_range=(10, 25),
            cumulative_time_ms=500.0,
            self_time_ms=400.0,
        )
        assert hs.function_name == "slow_func"
        assert hs.line_range == (10, 25)
        assert hs.cumulative_time_ms == 500.0

    def test_defaults(self):
        hs = HotSpot(
            function_name="f",
            file_path="f.py",
            line_range=(1, 5),
            cumulative_time_ms=10.0,
            self_time_ms=5.0,
        )
        assert hs.call_count == 0
        assert hs.is_c_extension is False
        assert hs.potential_speedup == 0.0

    def test_c_extension_flag(self):
        hs = HotSpot(
            function_name="_pickle.dumps",
            file_path="builtins",
            line_range=(0, 0),
            cumulative_time_ms=200.0,
            self_time_ms=200.0,
            is_c_extension=True,
            potential_speedup=5.0,
        )
        assert hs.is_c_extension is True
        assert hs.potential_speedup == 5.0


class TestProfileResult:
    def test_create_minimal(self):
        result = ProfileResult(script_path="run.py", duration_ms=1234.5)
        assert result.script_path == "run.py"
        assert result.duration_ms == 1234.5
        assert result.call_tree is None
        assert result.hotspots == []
        assert result.raw_stats_path is None

    def test_profile_id_auto_generated(self):
        r1 = ProfileResult(script_path="a.py", duration_ms=100)
        r2 = ProfileResult(script_path="b.py", duration_ms=200)
        assert r1.profile_id.startswith("prof_")
        assert r2.profile_id.startswith("prof_")
        assert r1.profile_id != r2.profile_id

    def test_timestamp_auto_generated(self):
        result = ProfileResult(script_path="x.py", duration_ms=50)
        assert result.timestamp is not None
        assert len(result.timestamp) > 0

    def test_full_result(self):
        tree = CallNode(function_name="main", file_path="m.py", line_number=1)
        hs = HotSpot(
            function_name="inner",
            file_path="i.py",
            line_range=(5, 20),
            cumulative_time_ms=300.0,
            self_time_ms=250.0,
        )
        result = ProfileResult(
            script_path="main.py",
            duration_ms=1000.0,
            call_tree=tree,
            hotspots=[hs],
            raw_stats_path="/tmp/prof.prof",
        )
        assert result.call_tree.function_name == "main"
        assert len(result.hotspots) == 1
        assert result.raw_stats_path == "/tmp/prof.prof"

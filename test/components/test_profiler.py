from __future__ import annotations

import io
import pstats
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from arwiz.foundation import CallNode, HotSpot, ProfileResult
from arwiz.process_manager import ProcessResult
from arwiz.profiler import DefaultProfiler
from arwiz.profiler.parsers import parse_pstats


def _fixture_target(name: str) -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / "targets" / name


def _max_tree_depth(node) -> int:
    if not node.children:
        return 1
    return 1 + max(_max_tree_depth(child) for child in node.children)


def test_profile_simple_script() -> None:
    profiler = DefaultProfiler()
    result = profiler.profile_script(_fixture_target("simple_loop.py"))

    assert result.duration_ms > 0
    assert result.script_path.endswith("simple_loop.py")


def test_profile_nested_calls() -> None:
    profiler = DefaultProfiler()
    result = profiler.profile_script(_fixture_target("nested_calls.py"))

    assert result.call_tree is not None
    assert _max_tree_depth(result.call_tree) > 1


def test_profile_numpy_heavy() -> None:
    profiler = DefaultProfiler()
    result = profiler.profile_script(_fixture_target("numpy_heavy.py"))

    assert len(result.hotspots) > 0


def test_call_tree_structure() -> None:
    profiler = DefaultProfiler()
    result = profiler.profile_script(_fixture_target("nested_calls.py"))

    root = result.call_tree
    assert root is not None
    assert root.children
    for child in root.children:
        for grandchild in child.children:
            assert grandchild.function_name


def test_hotspot_extraction() -> None:
    profiler = DefaultProfiler()
    result = profiler.profile_script(_fixture_target("simple_loop.py"))

    assert result.hotspots
    for hotspot in result.hotspots[:5]:
        assert hotspot.cumulative_time_ms >= hotspot.self_time_ms
        assert hotspot.call_count >= 0


def test_profile_id_unique() -> None:
    profiler = DefaultProfiler()

    first = profiler.profile_script(_fixture_target("simple_loop.py"))
    second = profiler.profile_script(_fixture_target("simple_loop.py"))

    assert first.profile_id != second.profile_id


def test_profile_with_args(tmp_path: Path) -> None:
    script = tmp_path / "args_target.py"
    script.write_text(
        "import sys\n"
        "def main():\n"
        "    n = int(sys.argv[1])\n"
        "    s = 0\n"
        "    for i in range(n):\n"
        "        s += i\n"
        "    print(s)\n"
        "if __name__ == '__main__':\n"
        "    main()\n",
        encoding="utf-8",
    )

    profiler = DefaultProfiler()
    result = profiler.profile_script(script, args=["5000"])

    assert result.duration_ms > 0
    assert result.script_path.endswith("args_target.py")


class TestProfilerErrorPaths:
    @pytest.mark.slow
    def test_profile_nonexistent_script(self, tmp_path: Path) -> None:
        profiler = DefaultProfiler()
        result = profiler.profile_script(tmp_path / "no_such_file.py")

        assert result.call_tree is None
        assert result.hotspots == []

    @pytest.mark.slow
    def test_profile_syntax_error_script(self, tmp_path: Path) -> None:
        script = tmp_path / "syntax_error.py"
        script.write_text("def broken(:\n  pass\n", encoding="utf-8")
        profiler = DefaultProfiler()
        result = profiler.profile_script(script)

        assert result.call_tree is None
        assert result.hotspots == []

    @pytest.mark.slow
    def test_profile_empty_script(self, tmp_path: Path) -> None:
        script = tmp_path / "empty.py"
        script.write_text("", encoding="utf-8")
        profiler = DefaultProfiler()
        result = profiler.profile_script(script)

        assert result.duration_ms >= 0
        assert isinstance(result.profile_id, str)

    @pytest.mark.slow
    def test_profile_import_crash_script(self, tmp_path: Path) -> None:
        script = tmp_path / "import_crash.py"
        script.write_text("raise RuntimeError('import crash')\n", encoding="utf-8")
        profiler = DefaultProfiler()
        result = profiler.profile_script(script)

        assert result.call_tree is None
        assert result.hotspots == []

    @pytest.mark.slow
    def test_profile_id_unique_across_many_runs(self, tmp_path: Path) -> None:
        script = tmp_path / "quick.py"
        script.write_text("x = 1\n", encoding="utf-8")
        profiler = DefaultProfiler()
        ids = {profiler.profile_script(script).profile_id for _ in range(5)}

        assert len(ids) == 5

    def test_profile_handles_timeout_gracefully(self, tmp_path: Path) -> None:
        mock_pm = MagicMock()
        mock_pm.run_script.return_value = ProcessResult(
            exit_code=-9,
            stdout="",
            stderr="Killed",
            timed_out=True,
            duration_ms=1500.0,
            pid=12345,
        )
        profiler = DefaultProfiler(process_manager=mock_pm)
        result = profiler.profile_script(tmp_path / "timeout.py")

        assert result.duration_ms > 0
        assert result.call_tree is None
        assert result.hotspots == []

    def test_parse_empty_pstats(self) -> None:
        import cProfile

        prof = cProfile.Profile()
        prof.enable()
        prof.disable()
        stats = pstats.Stats(prof, stream=io.StringIO())
        result = parse_pstats(stats, "/fake/script.py")

        assert isinstance(result, ProfileResult)
        assert result.script_path.endswith("script.py")

    def test_profile_result_json_serialization(self) -> None:
        node = CallNode(
            function_name="foo",
            file_path="/test.py",
            line_number=1,
        )
        hotspot = HotSpot(
            function_name="bar",
            file_path="/test.py",
            line_range=(5, 10),
            cumulative_time_ms=100.0,
            self_time_ms=50.0,
            call_count=10,
        )
        result = ProfileResult(
            script_path="/test.py",
            duration_ms=200.0,
            call_tree=node,
            hotspots=[hotspot],
        )
        json_str = result.model_dump_json()
        assert '"script_path"' in json_str
        assert '"hotspots"' in json_str

        restored = ProfileResult.model_validate_json(json_str)
        assert restored.script_path == result.script_path
        assert len(restored.hotspots) == 1
        assert restored.call_tree is not None
        assert restored.call_tree.function_name == "foo"

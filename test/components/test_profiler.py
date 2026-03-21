from __future__ import annotations

from pathlib import Path

from arwiz.profiler import DefaultProfiler


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

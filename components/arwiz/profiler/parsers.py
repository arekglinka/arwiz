from __future__ import annotations

import pstats
from pathlib import Path
from typing import cast

from arwiz.foundation import CallNode, HotSpot, ProfileResult


def _node_from_stat(
    func_key: tuple[str, int, str], stat: tuple[int, int, float, float, dict]
) -> CallNode:
    file_path, line_number, function_name = func_key
    _, nc, tt, ct, _ = stat
    return CallNode(
        function_name=function_name,
        file_path=file_path,
        line_number=line_number,
        cumulative_time_ms=ct * 1000,
        self_time_ms=tt * 1000,
        call_count=nc,
        children=[],
    )


def parse_pstats(stats: pstats.Stats, script_path: str) -> ProfileResult:
    stats.calc_callees()
    stats_map = cast("dict[tuple[str, int, str], tuple[int, int, float, float, dict]]", stats.stats)
    total_tt = float(getattr(stats, "total_tt", 0.0))

    callers_by_callee: dict[tuple[str, int, str], set[tuple[str, int, str]]] = {
        key: set() for key in stats_map
    }
    callees_by_caller: dict[tuple[str, int, str], set[tuple[str, int, str]]] = {
        key: set() for key in stats_map
    }

    for callee_key, stat in stats_map.items():
        callers = stat[4]
        for caller_key in callers:
            if caller_key in stats_map:
                callers_by_callee[callee_key].add(caller_key)
                callees_by_caller[caller_key].add(callee_key)

    script_real = str(Path(script_path).resolve())

    def _build_tree(func_key: tuple[str, int, str], stack: set[tuple[str, int, str]]) -> CallNode:
        base_node = _node_from_stat(func_key, stats_map[func_key])
        if func_key in stack:
            return base_node

        next_stack = set(stack)
        next_stack.add(func_key)
        children: list[CallNode] = []
        for callee_key in sorted(
            callees_by_caller.get(func_key, set()),
            key=lambda key: stats_map[key][3],
            reverse=True,
        ):
            children.append(_build_tree(callee_key, next_stack))
        base_node.children = children
        return base_node

    root_keys = [
        key for key in stats_map if key[0] == script_real or not callers_by_callee.get(key)
    ]
    root_children = [_build_tree(key, set()) for key in root_keys]

    root = CallNode(
        function_name="__root__",
        file_path=script_real,
        line_number=0,
        children=root_children,
        cumulative_time_ms=total_tt * 1000,
        self_time_ms=0.0,
        call_count=1,
    )

    sorted_stats = sorted(stats_map.items(), key=lambda item: item[1][3], reverse=True)
    hotspots: list[HotSpot] = []
    for func_key, stat in sorted_stats[:20]:
        file_path, line_number, function_name = func_key
        _, nc, tt, ct, _ = stat
        hotspots.append(
            HotSpot(
                function_name=function_name,
                file_path=file_path,
                line_range=(line_number, line_number),
                cumulative_time_ms=ct * 1000,
                self_time_ms=tt * 1000,
                call_count=nc,
                is_c_extension=file_path.startswith("~") or file_path in {"built-in", "<built-in>"},
                potential_speedup=0.0,
            )
        )

    return ProfileResult(
        script_path=script_real,
        duration_ms=total_tt * 1000,
        call_tree=root,
        hotspots=hotspots,
    )

"""Plotly-based flame graph visualization for profiling data."""

from __future__ import annotations

from typing import TYPE_CHECKING

import plotly.graph_objects as go

if TYPE_CHECKING:
    from arwiz.foundation import CallNode, HotSpot


def build_flame_graph(call_tree: CallNode | None, total_duration_ms: float) -> go.Figure:
    """Build a Plotly flame graph from call tree data."""
    if call_tree is None:
        return go.Figure().add_annotation(
            text="No profiling data available",
            xref="paper",
            yref="paper",
            showarrow=False,
            font={"size": 16},
        )

    x_positions: list[float] = []
    y_positions: list[int] = []
    widths: list[float] = []
    labels: list[str] = []
    hover_texts: list[str] = []
    colors: list[str] = []

    base_color = "#3b82f6"
    hotspot_color = "#ef4444"

    def traverse(node: CallNode, x_start: float, depth: int) -> float:
        if total_duration_ms <= 0:
            return x_start

        width = (node.cumulative_time_ms / total_duration_ms) * 100
        x_positions.append(x_start + width / 2)
        y_positions.append(depth)
        widths.append(width)
        labels.append(_truncate_label(node.function_name))

        hover = (
            f"<b>{node.function_name}</b><br>"
            f"File: {node.file_path}:{node.line_number}<br>"
            f"Self time: {node.self_time_ms:.2f}ms<br>"
            f"Cumulative: {node.cumulative_time_ms:.2f}ms<br>"
            f"Calls: {node.call_count}"
        )
        hover_texts.append(hover)
        colors.append(hotspot_color if node.self_time_ms > total_duration_ms * 0.1 else base_color)

        current_x = x_start
        for child in node.children:
            current_x = traverse(child, current_x, depth + 1)

        return x_start + width

    traverse(call_tree, 0, 0)

    max_depth = max(y_positions) if y_positions else 0

    fig = go.Figure()
    fig.add_bar(
        x=x_positions,
        y=[1] * len(x_positions),
        width=widths,
        base=y_positions,
        orientation="h",
        marker_color=colors,
        text=labels,
        textangle=0,
        hovertext=hover_texts,
        hoverinfo="text",
        customdata=widths,
    )

    fig.update_layout(
        title="Call Flame Graph",
        xaxis_title="Time Distribution (%)",
        yaxis_title="Call Depth",
        yaxis={
            "autorange": "reversed",
            "dtick": 1,
            "range": [max_depth + 0.5, -0.5],
        },
        xaxis={"range": [0, 100]},
        height=400,
        showlegend=False,
        bargap=0.02,
    )

    return fig


def _truncate_label(name: str, max_len: int = 20) -> str:
    if len(name) <= max_len:
        return name
    return name[: max_len - 3] + "..."


def build_call_tree_table(call_tree: CallNode | None) -> list[dict]:
    """Flatten call tree to table rows for display."""
    rows: list[dict] = []

    if call_tree is None:
        return rows

    def traverse(node: CallNode, depth: int) -> None:
        indent = "  " * depth
        rows.append(
            {
                "function": f"{indent}{node.function_name}",
                "file": f"{node.file_path}:{node.line_number}",
                "self_ms": round(node.self_time_ms, 2),
                "cumulative_ms": round(node.cumulative_time_ms, 2),
                "calls": node.call_count,
            }
        )
        for child in node.children:
            traverse(child, depth + 1)

    traverse(call_tree, 0)
    return rows


def build_hotspots_table(hotspots: list[HotSpot]) -> list[dict]:
    """Convert hotspots to table rows."""
    return [
        {
            "function": hs.function_name,
            "file": f"{hs.file_path}:{hs.line_range[0]}",
            "self_ms": round(hs.self_time_ms, 2),
            "cumulative_ms": round(hs.cumulative_time_ms, 2),
            "calls": hs.call_count,
            "potential_speedup": f"{hs.potential_speedup:.1f}%",
        }
        for hs in hotspots
    ]

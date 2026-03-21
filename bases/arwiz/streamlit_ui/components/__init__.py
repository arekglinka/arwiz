"""UI components for arwiz Streamlit interface."""

from arwiz.streamlit_ui.components.code_diff import (
    compute_line_diff,
    format_code_for_display,
    get_diff_stats,
)
from arwiz.streamlit_ui.components.flame_graph import (
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

__all__ = [
    "build_flame_graph",
    "build_call_tree_table",
    "build_hotspots_table",
    "format_code_for_display",
    "compute_line_diff",
    "get_diff_stats",
    "format_speedup",
    "get_speedup_color",
    "format_equivalence_result",
    "build_metrics_display",
    "build_timing_display",
]

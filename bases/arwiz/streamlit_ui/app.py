"""Main Streamlit application for arwiz profiling and optimization.

Brick: bases/arwiz/streamlit_ui
Run with: streamlit run -m arwiz.streamlit_ui.app
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st
from arwiz.coverage_tracer import DefaultCoverageTracer
from arwiz.hotspot import DefaultHotspotDetector
from arwiz.llm_optimizer import DefaultLLMOptimizer
from arwiz.profiler import DefaultProfiler
from arwiz.streamlit_ui.components import (
    build_call_tree_table,
    build_flame_graph,
    build_hotspots_table,
    build_metrics_display,
    get_diff_stats,
)
from arwiz.streamlit_ui.state import get_state, reset_state
from arwiz.template_optimizer import DefaultTemplateOptimizer


def render_sidebar() -> dict:
    st.sidebar.header("Configuration")

    script_path = st.sidebar.text_input(
        "Script Path",
        value="",
        placeholder="/path/to/script.py",
    )

    script_args = st.sidebar.text_input(
        "Script Arguments",
        value="",
        placeholder="arg1 arg2 --flag value",
    )

    args_list = script_args.split() if script_args else []

    st.sidebar.divider()
    st.sidebar.subheader("Profiling Settings")

    threshold_pct = st.sidebar.slider(
        "Hotspot Threshold (%)",
        min_value=1.0,
        max_value=50.0,
        value=5.0,
        step=0.5,
    )

    warmup_runs = st.sidebar.number_input(
        "Warmup Runs",
        min_value=0,
        max_value=10,
        value=1,
    )

    st.sidebar.divider()
    st.sidebar.subheader("Optimization Settings")

    strategy = st.sidebar.selectbox(
        "Strategy",
        options=["auto", "llm", "template"],
        index=0,
    )

    template_name = st.sidebar.selectbox(
        "Template",
        options=["vectorize_loop", "numba_jit", "add_caching", "batch_io"],
        index=0,
        disabled=(strategy != "template"),
    )

    st.sidebar.divider()

    if st.sidebar.button("Reset State", type="secondary"):
        reset_state()
        st.rerun()

    return {
        "script_path": script_path,
        "args": args_list,
        "threshold_pct": threshold_pct,
        "warmup_runs": warmup_runs,
        "strategy": strategy,
        "template_name": template_name,
    }


def render_profiling_tab(config: dict) -> None:
    state = get_state()

    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("Profile Script")
    with col2:
        run_profile = st.button("Run Profile", type="primary", key="run_profile_btn")

    if run_profile and config["script_path"]:
        with st.spinner("Profiling script..."):
            try:
                profiler = DefaultProfiler()
                from arwiz.foundation import ProfilingConfig

                prof_config = ProfilingConfig(warmup_runs=config["warmup_runs"])
                state.profile_result = profiler.profile_script(
                    config["script_path"],
                    args=config["args"],
                    config=prof_config,
                )

                detector = DefaultHotspotDetector()
                state.hotspots = detector.detect_hotspots(
                    state.profile_result, threshold_pct=config["threshold_pct"]
                )
            except Exception as e:
                st.error(f"Profiling failed: {e}")
                return

    if state.profile_result is None:
        st.info("Run a profile to see results here.")
        return

    st.metric(
        "Total Duration",
        f"{state.profile_result.duration_ms:.2f}ms",
    )

    st.subheader("Flame Graph")
    fig = build_flame_graph(
        state.profile_result.call_tree,
        state.profile_result.duration_ms,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Call Tree")
    tree_rows = build_call_tree_table(state.profile_result.call_tree)
    if tree_rows:
        st.dataframe(
            tree_rows,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No call tree data available.")

    st.subheader("Hotspots")
    hotspot_rows = build_hotspots_table(state.hotspots)
    if hotspot_rows:
        st.dataframe(
            hotspot_rows,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No hotspots detected above threshold.")


def render_optimization_tab(config: dict) -> None:
    state = get_state()

    if not state.hotspots:
        st.warning("Run profiling first to detect hotspots for optimization.")
        return

    st.subheader("Select Function to Optimize")

    hotspot_options = [
        f"{hs.function_name} ({hs.file_path}:{hs.line_range[0]})" for hs in state.hotspots
    ]

    selected_idx = st.selectbox(
        "Hotspot",
        range(len(hotspot_options)),
        format_func=lambda i: hotspot_options[i],
        key="hotspot_selector",
    )
    state.selected_hotspot_idx = selected_idx

    selected_hotspot = state.hotspots[selected_idx]

    st.write("**Selected Hotspot:**")
    st.json(
        {
            "function": selected_hotspot.function_name,
            "file": selected_hotspot.file_path,
            "self_time_ms": selected_hotspot.self_time_ms,
            "cumulative_time_ms": selected_hotspot.cumulative_time_ms,
            "potential_speedup": f"{selected_hotspot.potential_speedup:.1f}%",
        }
    )

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        strategy = st.selectbox(
            "Optimization Strategy",
            options=["auto", "llm", "template"],
            index=0,
            key="opt_strategy",
        )
    with col2:
        template_name = st.selectbox(
            "Template (if strategy=template)",
            options=["vectorize_loop", "numba_jit", "add_caching", "batch_io"],
            index=0,
            key="opt_template",
        )

    state.original_code = st.text_area(
        "Original Code",
        value=state.original_code,
        height=200,
        placeholder="Paste the function code to optimize...",
    )

    if st.button("Generate Optimization", type="primary"):
        if not state.original_code.strip():
            st.error("Please provide the original code to optimize.")
        else:
            with st.spinner("Generating optimization..."):
                try:
                    if strategy == "template":
                        optimizer = DefaultTemplateOptimizer()
                        optimized = optimizer.apply_template(state.original_code, template_name)
                        state.optimization_attempt = None
                        state.optimized_code = optimized
                    else:
                        llm_optimizer = DefaultLLMOptimizer()
                        attempt = llm_optimizer.optimize_function(
                            state.original_code,
                            selected_hotspot,
                        )
                        state.optimization_attempt = attempt
                        state.optimized_code = attempt.optimized_code
                except Exception as e:
                    st.error(f"Optimization failed: {e}")
                    return

    if state.optimized_code:
        st.divider()
        st.subheader("Code Diff")

        col_orig, col_opt = st.columns(2)
        with col_orig:
            st.markdown("**Original**")
            st.code(state.original_code, language="python")
        with col_opt:
            st.markdown("**Optimized**")
            st.code(state.optimized_code, language="python")

        diff_stats = get_diff_stats(state.original_code, state.optimized_code)
        st.caption(
            f"Lines: {diff_stats['original_lines']} → {diff_stats['optimized_lines']} "
            f"({diff_stats['line_delta']:+d})"
        )

        if state.optimization_attempt:
            st.divider()
            st.subheader("Optimization Metrics")

            metrics = build_metrics_display(state.optimization_attempt)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Speedup", metrics["speedup"])
            with col2:
                st.metric(
                    "Syntax Valid",
                    "Yes" if metrics["syntax_valid"] else "No",
                    delta=None if metrics["syntax_valid"] else "ERROR",
                    delta_color="off" if metrics["syntax_valid"] else "inverse",
                )
            with col3:
                st.metric(
                    "Strategy",
                    metrics["strategy"],
                )

            if metrics.get("error_message"):
                st.error(f"Error: {metrics['error_message']}")

        if st.button("Apply Optimization", type="secondary"):
            st.info(
                "Apply functionality requires file system write access. "
                "Copy the optimized code manually."
            )


def render_coverage_tab(config: dict) -> None:
    state = get_state()

    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("Branch Coverage")
    with col2:
        run_trace = st.button("Run Trace", type="primary", key="run_trace_btn")

    if run_trace and config["script_path"]:
        with st.spinner("Tracing branch coverage..."):
            try:
                tracer = DefaultCoverageTracer()
                state.coverage = tracer.trace_branches(
                    config["script_path"],
                    args=config["args"],
                )
            except Exception as e:
                st.error(f"Coverage tracing failed: {e}")
                return

    if state.coverage is None:
        st.info("Run a trace to see coverage results here.")
        return

    st.metric(
        "Branch Coverage",
        f"{state.coverage.coverage_percent:.1f}%",
        delta=f"{state.coverage.covered_branches}/{state.coverage.total_branches}",
    )

    st.subheader("Coverage Distribution")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=["Covered", "Uncovered"],
            y=[
                state.coverage.covered_branches,
                state.coverage.total_branches - state.coverage.covered_branches,
            ],
            marker_color=["#22c55e", "#ef4444"],
        )
    )
    fig.update_layout(
        title="Branch Coverage",
        yaxis_title="Branches",
        height=300,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Uncovered Branches")
    if state.coverage.uncovered_lines:
        uncovered_data = [
            {
                "Line": line,
                "Type": next(
                    (
                        bi.branch_type
                        for bi in state.coverage.branch_details
                        if bi.line_number == line
                    ),
                    "unknown",
                ),
            }
            for line in state.coverage.uncovered_lines
        ]
        st.dataframe(uncovered_data, use_container_width=True, hide_index=True)
    else:
        st.success("All branches covered!")


def main() -> None:
    st.set_page_config(
        page_title="Arwiz - Python Profiling & Optimization",
        page_icon="profiler",
        layout="wide",
    )

    st.title("Arwiz Profiler & Optimizer")

    config = render_sidebar()

    tab_profile, tab_optimize, tab_coverage = st.tabs(["Profiling", "Optimization", "Coverage"])

    with tab_profile:
        render_profiling_tab(config)

    with tab_optimize:
        render_optimization_tab(config)

    with tab_coverage:
        render_coverage_tab(config)


if __name__ == "__main__":
    main()

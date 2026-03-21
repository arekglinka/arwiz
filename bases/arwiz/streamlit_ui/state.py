"""Session state management for Streamlit UI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from arwiz.foundation import (
        BranchCoverage,
        HotSpot,
        OptimizationAttempt,
        ProfileResult,
    )


@dataclass
class SessionState:
    """Manages cached results between Streamlit interactions."""

    profile_result: ProfileResult | None = None
    hotspots: list[HotSpot] = field(default_factory=list)
    coverage: BranchCoverage | None = None
    optimization_attempt: OptimizationAttempt | None = None
    selected_hotspot_idx: int = 0
    selected_strategy: str = "auto"
    selected_template: str = "vectorize_loop"
    original_code: str = ""
    optimized_code: str = ""

    def clear(self) -> None:
        self.profile_result = None
        self.hotspots = []
        self.coverage = None
        self.optimization_attempt = None
        self.selected_hotspot_idx = 0
        self.original_code = ""
        self.optimized_code = ""


def get_state() -> SessionState:
    """Get or create session state from Streamlit's session_state."""
    import streamlit as st

    if "arwiz_state" not in st.session_state:
        st.session_state.arwiz_state = SessionState()
    return st.session_state.arwiz_state


def reset_state() -> None:
    """Clear all cached state."""
    import streamlit as st

    if "arwiz_state" in st.session_state:
        st.session_state.arwiz_state.clear()
    else:
        st.session_state.arwiz_state = SessionState()

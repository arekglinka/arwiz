"""Display optimization metrics and results."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from arwiz.foundation import OptimizationAttempt


def format_speedup(speedup_percent: float) -> str:
    """Format speedup percentage for display."""
    if speedup_percent > 0:
        return f"+{speedup_percent:.1f}%"
    if speedup_percent < 0:
        return f"{speedup_percent:.1f}%"
    return "0.0%"


def get_speedup_color(speedup_percent: float) -> str:
    """Get color for speedup display based on magnitude."""
    if speedup_percent >= 50:
        return "green"
    if speedup_percent >= 20:
        return "lightgreen"
    if speedup_percent >= 0:
        return "gray"
    return "red"


def format_equivalence_result(passed: bool, error_msg: str | None) -> dict:
    """Format equivalence test result for display."""
    if passed:
        return {"status": "PASSED", "color": "green", "icon": "check", "message": "Outputs match"}
    return {
        "status": "FAILED",
        "color": "red",
        "icon": "x",
        "message": error_msg or "Outputs differ",
    }


def build_metrics_display(attempt: OptimizationAttempt | None) -> dict:
    """Build metrics dictionary for display from optimization attempt."""
    if attempt is None:
        return {
            "speedup": "N/A",
            "speedup_color": "gray",
            "syntax_valid": None,
            "equivalence": None,
            "strategy": "N/A",
            "model": "N/A",
        }

    eq_result = format_equivalence_result(attempt.passed_equivalence, attempt.error_message)

    return {
        "speedup": format_speedup(attempt.speedup_percent),
        "speedup_color": get_speedup_color(attempt.speedup_percent),
        "speedup_raw": attempt.speedup_percent,
        "syntax_valid": attempt.syntax_valid,
        "syntax_color": "green" if attempt.syntax_valid else "red",
        "equivalence": eq_result,
        "strategy": attempt.strategy,
        "model": attempt.llm_model or attempt.template_name or "N/A",
        "has_error": attempt.error_message is not None,
        "error_message": attempt.error_message,
    }


def build_timing_display(duration_ms: float, label: str = "Execution") -> dict:
    """Build timing display dictionary."""
    if duration_ms < 1000:
        time_str = f"{duration_ms:.2f}ms"
    elif duration_ms < 60000:
        time_str = f"{duration_ms / 1000:.2f}s"
    else:
        time_str = f"{duration_ms / 60000:.2f}m"

    return {"label": label, "value": time_str, "raw_ms": duration_ms}

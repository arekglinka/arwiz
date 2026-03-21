"""Side-by-side code diff viewer component."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def format_code_for_display(code: str, max_lines: int = 100) -> str:
    """Format code for display in a code block."""
    lines = code.strip().split("\n")
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines.append(f"\n... ({len(lines) - max_lines} more lines)")
    return "\n".join(lines)


def compute_line_diff(
    original: str, optimized: str
) -> tuple[list[tuple[int, str, str]], list[tuple[int, str, str]]]:
    """Compute simple line-by-line diff for display.

    Returns tuples of (line_number, line_content, status) where status is
    'unchanged', 'added', or 'removed'.
    """
    orig_lines = original.strip().split("\n") if original.strip() else []
    opt_lines = optimized.strip().split("\n") if optimized.strip() else []

    orig_result: list[tuple[int, str, str]] = []
    opt_result: list[tuple[int, str, str]] = []

    max_len = max(len(orig_lines), len(opt_lines))

    for i in range(max_len):
        orig_line = orig_lines[i] if i < len(orig_lines) else ""
        opt_line = opt_lines[i] if i < len(opt_lines) else ""

        if orig_line == opt_line:
            orig_result.append((i + 1, orig_line, "unchanged"))
            opt_result.append((i + 1, opt_line, "unchanged"))
        else:
            if i < len(orig_lines) and i >= len(opt_lines):
                orig_result.append((i + 1, orig_line, "removed"))
            elif i < len(opt_lines) and i >= len(orig_lines):
                opt_result.append((i + 1, opt_line, "added"))
            else:
                orig_result.append((i + 1, orig_line, "removed"))
                opt_result.append((i + 1, opt_line, "added"))

    return orig_result, opt_result


def get_diff_stats(original: str, optimized: str) -> dict:
    """Compute diff statistics for display."""
    orig_lines = len(original.strip().split("\n")) if original.strip() else 0
    opt_lines = len(optimized.strip().split("\n")) if optimized.strip() else 0

    return {
        "original_lines": orig_lines,
        "optimized_lines": opt_lines,
        "line_delta": opt_lines - orig_lines,
    }

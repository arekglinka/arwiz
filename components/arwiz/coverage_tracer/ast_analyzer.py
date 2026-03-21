"""AST-based static branch analysis."""

from __future__ import annotations

import ast
from pathlib import Path


def get_static_branches(script_path: Path) -> list[dict]:
    """Parse AST and find all branch points.

    Walks the AST tree to find If, For, While, and Try nodes,
    returning metadata about each branch point.

    Args:
        script_path: Path to the Python script to analyze.

    Returns:
        List of dicts with 'line', 'type', and 'condition' keys.
    """
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))

    branches: list[dict] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            condition = _unparse(node.test)
            branches.append({"line": node.lineno, "type": "If", "condition": condition})
        elif isinstance(node, (ast.For, ast.While)):
            if isinstance(node, ast.For):
                condition = f"for {ast.unparse(node.target)} in ..."
            else:
                condition = _unparse(node.test)
            branches.append(
                {"line": node.lineno, "type": type(node).__name__, "condition": condition}
            )
        elif isinstance(node, ast.Try):
            branches.append({"line": node.lineno, "type": "Try", "condition": "try"})

    return branches


def _unparse(node: ast.expr) -> str:
    """Safely unparse an AST expression node."""
    try:
        return ast.unparse(node)
    except Exception:
        return "<unparseable>"

"""AST-based static branch detection.

Parses Python source files and identifies all branch points
(if/elif/else, for, while, try/except) with their line numbers.
"""

from __future__ import annotations

import ast
from pathlib import Path


class _BranchVisitor(ast.NodeVisitor):
    """Visits AST nodes to collect branch points."""

    def __init__(self) -> None:
        self.branches: list[tuple[int, str]] = []

    def visit_If(self, node: ast.If) -> None:
        """Collect if/elif/else branches."""
        self.branches.append((node.lineno, "if"))
        self._collect_elif_chain(node)
        self.generic_visit(node)

    def _collect_elif_chain(self, node: ast.If) -> None:
        """Recursively collect elif/else branches from an If node's orelse."""
        if node.orelse:
            if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                elif_node = node.orelse[0]
                self.branches.append((elif_node.lineno, "elif"))
                self._collect_elif_chain(elif_node)
            else:
                # else branch — use first statement line
                else_line = node.orelse[0].lineno if node.orelse else node.lineno
                self.branches.append((else_line, "else"))

    def visit_For(self, node: ast.For) -> None:
        """Collect for-loop branches."""
        self.branches.append((node.lineno, "for"))
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        """Collect while-loop branches."""
        self.branches.append((node.lineno, "while"))
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:
        """Collect try/except branches."""
        self.branches.append((node.lineno, "try"))
        for handler in node.handlers:
            self.branches.append((handler.lineno, "except"))
        # else block
        if node.orelse:
            self.branches.append((node.orelse[0].lineno, "try_else"))
        # finally block
        if node.finalbody:
            self.branches.append((node.finalbody[0].lineno, "finally"))
        self.generic_visit(node)


def get_static_branches(script_path: Path | str) -> list[tuple[int, str]]:
    """Parse a Python file and return all branch points.

    Walks the AST to find if/elif/else, for, while, and try/except nodes.

    Args:
        script_path: Path to the Python source file.

    Returns:
        List of (line_number, branch_type) tuples.

    Raises:
        FileNotFoundError: If the script file does not exist.
        SyntaxError: If the script has invalid Python syntax.
    """
    path = Path(script_path)
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))

    visitor = _BranchVisitor()
    visitor.visit(tree)

    return visitor.branches

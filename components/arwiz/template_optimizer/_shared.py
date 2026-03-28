"""Shared utilities for AST template transformers."""

from __future__ import annotations

import ast


def has_import(tree: ast.Module, module_name: str) -> bool:
    """Check if a module import exists in the AST tree.

    Checks for both ``import {module_name}`` and ``from {module_name} import ...``.
    Also handles dotted module names like ``jax.numpy``.
    """
    for stmt in tree.body:
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                if alias.name == module_name or alias.name.startswith(f"{module_name}."):
                    return True
        if (
            isinstance(stmt, ast.ImportFrom)
            and stmt.module
            and (stmt.module == module_name or stmt.module.startswith(f"{module_name}."))
        ):
            return True
    return False


def apply_transformer(
    source_code: str,
    transformer: ast.NodeTransformer,
    import_to_add: str | None = None,
    import_names: list[str] | None = None,
) -> str:
    """Apply an AST transformer with standardized error handling and import injection.

    Args:
        source_code: The source code to transform.
        transformer: The AST NodeTransformer to apply.
        import_to_add: Module name to import if not already present (e.g., ``"cython"``).
        import_names: For ``from X import Y`` style. If provided, *import_to_add*
            is the ``from`` part.

    Returns:
        Transformed source code, or original if transformation fails.
    """
    try:
        tree = ast.parse(source_code)
    except (SyntaxError, ValueError):
        return source_code

    try:
        transformed = transformer.visit(tree)
        if not isinstance(transformed, ast.Module):
            return source_code

        if getattr(transformer, "modified", False) and import_to_add is not None:
            if import_names is not None:
                # from X import Y, Z
                if not has_import(transformed, import_to_add):
                    aliases = [ast.alias(name=name) for name in import_names]
                    import_node = ast.ImportFrom(module=import_to_add, names=aliases, level=0)
                    transformed.body.insert(0, import_node)
            else:
                # import X
                if not has_import(transformed, import_to_add):
                    import_node = ast.Import(names=[ast.alias(name=import_to_add)])
                    transformed.body.insert(0, import_node)

        ast.fix_missing_locations(transformed)
        return ast.unparse(transformed)
    except (SyntaxError, ValueError, TypeError):
        return source_code

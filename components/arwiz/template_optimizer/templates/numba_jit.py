import ast


def _is_numba_jit_decorator(decorator: ast.expr) -> bool:
    if isinstance(decorator, ast.Attribute) and isinstance(decorator.value, ast.Name):
        return decorator.value.id == "numba" and decorator.attr in {"njit", "jit"}

    if isinstance(decorator, ast.Name):
        return decorator.id in {"njit", "jit"}

    if isinstance(decorator, ast.Call):
        return _is_numba_jit_decorator(decorator.func)

    deco_text = ast.unparse(decorator)
    return (
        "numba" in deco_text
        or "njit" in deco_text
        or deco_text == "jit"
        or deco_text.endswith(".jit")
    )


class _NumbaJITAdder(ast.NodeTransformer):
    def __init__(self) -> None:
        self.modified = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        self.generic_visit(node)
        has_decorator = any(_is_numba_jit_decorator(deco) for deco in node.decorator_list)
        if not has_decorator:
            self.modified = True
            node.decorator_list.insert(
                0,
                ast.Attribute(
                    value=ast.Name(id="numba", ctx=ast.Load()),
                    attr="njit",
                    ctx=ast.Load(),
                ),
            )
        return node


def _has_numba_import(tree: ast.Module) -> bool:
    for stmt in tree.body:
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                if alias.name == "numba":
                    return True
        if isinstance(stmt, ast.ImportFrom) and stmt.module == "numba":
            return True
    return False


def apply_numba_jit(source_code: str) -> str:
    tree = ast.parse(source_code)
    transformer = _NumbaJITAdder()
    transformed = transformer.visit(tree)
    if (
        transformer.modified
        and isinstance(transformed, ast.Module)
        and not _has_numba_import(transformed)
    ):
        transformed.body.insert(0, ast.Import(names=[ast.alias(name="numba", asname=None)]))
    ast.fix_missing_locations(transformed)
    return ast.unparse(transformed)


add_numba_jit = apply_numba_jit

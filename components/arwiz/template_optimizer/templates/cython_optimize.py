import ast

from .._shared import has_import


def _is_cython_cfunc_decorator(decorator: ast.expr) -> bool:
    if isinstance(decorator, ast.Attribute) and isinstance(decorator.value, ast.Name):
        return decorator.value.id == "cython" and decorator.attr == "cfunc"

    if isinstance(decorator, ast.Name):
        return decorator.id == "cfunc"

    if isinstance(decorator, ast.Call):
        return _is_cython_cfunc_decorator(decorator.func)

    return "cython.cfunc" in ast.unparse(decorator)


def _function_uses_name(node: ast.FunctionDef, name: str) -> bool:
    return any(isinstance(inner, ast.Name) and inner.id == name for inner in ast.walk(node))


class _CythonTransformer(ast.NodeTransformer):
    def __init__(self) -> None:
        self.modified = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        self.generic_visit(node)

        has_cfunc = any(_is_cython_cfunc_decorator(deco) for deco in node.decorator_list)
        if not has_cfunc:
            node.decorator_list.insert(
                0,
                ast.Attribute(
                    value=ast.Name(id="cython", ctx=ast.Load()),
                    attr="cfunc",
                    ctx=ast.Load(),
                ),
            )
            self.modified = True

        indexed_names: set[str] = set()
        loop_index_vars: set[str] = set()
        for inner in ast.walk(node):
            if isinstance(inner, ast.For) and isinstance(inner.target, ast.Name):
                loop_index_vars.add(inner.target.id)
            if isinstance(inner, ast.Subscript) and isinstance(inner.value, ast.Name):
                indexed_names.add(inner.value.id)

        for arg in node.args.args:
            if arg.arg in indexed_names and arg.annotation is None:
                arg.annotation = ast.Subscript(
                    value=ast.Attribute(
                        value=ast.Name(id="cython", ctx=ast.Load()),
                        attr="double",
                        ctx=ast.Load(),
                    ),
                    slice=ast.Slice(lower=None, upper=None, step=None),
                    ctx=ast.Load(),
                )
                self.modified = True

        existing_annotations: set[str] = set()
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                existing_annotations.add(stmt.target.id)

        annotation_stmts: list[ast.stmt] = []
        for var_name in sorted(loop_index_vars):
            if var_name in existing_annotations:
                continue
            if _function_uses_name(node, var_name):
                annotation_stmts.append(
                    ast.AnnAssign(
                        target=ast.Name(id=var_name, ctx=ast.Store()),
                        annotation=ast.Attribute(
                            value=ast.Name(id="cython", ctx=ast.Load()),
                            attr="int",
                            ctx=ast.Load(),
                        ),
                        value=None,
                        simple=1,
                    )
                )
                self.modified = True

        if annotation_stmts:
            node.body = [*annotation_stmts, *node.body]

        return node


def apply_cython_optimize(source_code: str) -> str:
    try:
        tree = ast.parse(source_code)
    except (SyntaxError, ValueError):
        return source_code

    transformer = _CythonTransformer()
    transformed = transformer.visit(tree)
    if (
        transformer.modified
        and isinstance(transformed, ast.Module)
        and not has_import(transformed, "cython")
    ):
        transformed.body.insert(0, ast.Import(names=[ast.alias(name="cython", asname=None)]))
    ast.fix_missing_locations(transformed)
    rendered = ast.unparse(transformed)
    directive = "# cython: boundscheck=False, wraparound=False"
    if not rendered.startswith(directive):
        rendered = f"{directive}\n{rendered}"
    return rendered


cython_optimize = apply_cython_optimize

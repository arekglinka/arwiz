import ast


def _is_cupy_asarray_call(expr: ast.expr, arg_name: str) -> bool:
    if not isinstance(expr, ast.Call):
        return False
    if not (
        isinstance(expr.func, ast.Attribute)
        and isinstance(expr.func.value, ast.Name)
        and expr.func.value.id == "cp"
        and expr.func.attr == "asarray"
    ):
        return False
    if len(expr.args) != 1 or expr.keywords:
        return False
    arg = expr.args[0]
    return isinstance(arg, ast.Name) and arg.id == arg_name


def _is_cupy_asnumpy_call(expr: ast.expr) -> bool:
    return (
        isinstance(expr, ast.Call)
        and isinstance(expr.func, ast.Attribute)
        and isinstance(expr.func.value, ast.Name)
        and expr.func.value.id == "cp"
        and expr.func.attr == "asnumpy"
    )


def _has_cupy_alias_cp(stmt: ast.stmt) -> bool:
    if isinstance(stmt, ast.Import):
        for alias in stmt.names:
            if alias.name == "cupy" and alias.asname == "cp":
                return True
    return False


class _CuPyTransformer(ast.NodeTransformer):
    def __init__(self) -> None:
        self.modified = False

    def visit_Import(self, node: ast.Import) -> ast.AST:
        updated_aliases: list[ast.alias] = []
        changed = False
        for alias in node.names:
            if (alias.name == "numpy" and alias.asname is None) or (
                alias.name == "cupy" and alias.asname is None
            ):
                updated_aliases.append(ast.alias(name="cupy", asname="cp"))
                changed = True
            else:
                updated_aliases.append(alias)
        if changed:
            self.modified = True
            node.names = updated_aliases
        return node

    def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
        self.generic_visit(node)
        if isinstance(node.value, ast.Name) and node.value.id == "np":
            node.value = ast.Name(id="cp", ctx=ast.Load())
            self.modified = True
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        self.generic_visit(node)

        params = [
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
        ]
        if node.args.vararg is not None:
            params.append(node.args.vararg)
        if node.args.kwarg is not None:
            params.append(node.args.kwarg)

        converted_params: set[str] = set()
        for stmt in node.body:
            if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
                call = stmt.value
                if (
                    isinstance(call.func, ast.Attribute)
                    and isinstance(call.func.value, ast.Name)
                    and call.func.value.id == "cp"
                    and call.func.attr == "asarray"
                ):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name):
                            converted_params.add(target.id)

        conversion_stmts: list[ast.stmt] = []
        for arg in params:
            if arg.arg in {"self", "cls"}:
                continue
            if arg.arg in converted_params:
                continue
            conversion_stmts.append(
                ast.Assign(
                    targets=[ast.Name(id=arg.arg, ctx=ast.Store())],
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id="cp", ctx=ast.Load()),
                            attr="asarray",
                            ctx=ast.Load(),
                        ),
                        args=[ast.Name(id=arg.arg, ctx=ast.Load())],
                        keywords=[],
                    ),
                )
            )

        if conversion_stmts:
            node.body = [*conversion_stmts, *node.body]
            self.modified = True
        return node

    def visit_Return(self, node: ast.Return) -> ast.AST:
        self.generic_visit(node)
        if node.value is None or _is_cupy_asnumpy_call(node.value):
            return node
        node.value = ast.Call(
            func=ast.Attribute(
                value=ast.Name(id="cp", ctx=ast.Load()),
                attr="asnumpy",
                ctx=ast.Load(),
            ),
            args=[node.value],
            keywords=[],
        )
        self.modified = True
        return node


def apply_cupy_optimize(source_code: str) -> str:
    try:
        tree = ast.parse(source_code)
    except (SyntaxError, ValueError):
        return source_code
    transformer = _CuPyTransformer()
    transformed = transformer.visit(tree)
    if (
        transformer.modified
        and isinstance(transformed, ast.Module)
        and not any(_has_cupy_alias_cp(stmt) for stmt in transformed.body)
    ):
        transformed.body.insert(0, ast.Import(names=[ast.alias(name="cupy", asname="cp")]))
    ast.fix_missing_locations(transformed)
    return ast.unparse(transformed)

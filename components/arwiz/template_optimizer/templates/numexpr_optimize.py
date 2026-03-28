import ast


def _has_numexpr_import(tree: ast.Module) -> bool:
    for stmt in tree.body:
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                if alias.name == "numexpr":
                    return True
        if isinstance(stmt, ast.ImportFrom) and stmt.module == "numexpr":
            return True
    return False


def _is_arithmetic_expr(node: ast.AST) -> bool:
    if isinstance(node, ast.BinOp):
        return (
            isinstance(
                node.op,
                (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv),
            )
            and _is_arithmetic_expr(node.left)
            and _is_arithmetic_expr(node.right)
        )
    if isinstance(node, ast.UnaryOp):
        return isinstance(node.op, (ast.UAdd, ast.USub)) and _is_arithmetic_expr(node.operand)
    if isinstance(node, ast.Subscript):
        return isinstance(node.value, ast.Name)
    return bool(isinstance(node, ast.Name | ast.Constant))


class _NumExprExpressionRewriter(ast.NodeTransformer):
    def __init__(self, iter_name: str) -> None:
        self.iter_name = iter_name

    def visit_Subscript(self, node: ast.Subscript) -> ast.AST:
        self.generic_visit(node)
        if (
            isinstance(node.value, ast.Name)
            and isinstance(node.slice, ast.Name)
            and node.slice.id == self.iter_name
        ):
            return ast.Name(id=node.value.id, ctx=ast.Load())
        return node


class _NumExprTransformer(ast.NodeTransformer):
    def __init__(self) -> None:
        self.modified = False

    def _build_numexpr_assign(self, target_name: str, expr: ast.expr) -> ast.Assign:
        expr_text = ast.unparse(expr)
        return ast.Assign(
            targets=[ast.Name(id=target_name, ctx=ast.Store())],
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id="numexpr", ctx=ast.Load()),
                    attr="evaluate",
                    ctx=ast.Load(),
                ),
                args=[ast.Constant(value=expr_text)],
                keywords=[],
            ),
        )

    def visit_For(self, node: ast.For) -> ast.AST:
        self.generic_visit(node)
        if not isinstance(node.target, ast.Name):
            return node
        if node.orelse:
            return node
        if len(node.body) != 1:
            return node

        stmt = node.body[0]
        if not isinstance(stmt, ast.Assign):
            return node
        if len(stmt.targets) != 1:
            return node
        target = stmt.targets[0]
        if not isinstance(target, ast.Subscript):
            return node
        if not isinstance(target.value, ast.Name):
            return node
        if not isinstance(target.slice, ast.Name) or target.slice.id != node.target.id:
            return node
        if not _is_arithmetic_expr(stmt.value):
            return node

        rewritten_expr = _NumExprExpressionRewriter(node.target.id).visit(stmt.value)
        if not isinstance(rewritten_expr, ast.expr):
            return node

        self.modified = True
        return ast.fix_missing_locations(
            self._build_numexpr_assign(target.value.id, rewritten_expr)
        )


def apply_numexpr_optimize(source_code: str) -> str:
    tree = ast.parse(source_code)
    transformer = _NumExprTransformer()
    transformed = transformer.visit(tree)
    if (
        transformer.modified
        and isinstance(transformed, ast.Module)
        and not _has_numexpr_import(transformed)
    ):
        transformed.body.insert(0, ast.Import(names=[ast.alias(name="numexpr", asname=None)]))
    ast.fix_missing_locations(transformed)
    return ast.unparse(transformed)

import ast


class _BatchIOTransformer(ast.NodeTransformer):
    def visit_With(self, node: ast.With) -> ast.AST:
        self.generic_visit(node)
        if len(node.body) != 1 or not isinstance(node.body[0], ast.For):
            return node
        loop = node.body[0]
        if len(loop.body) != 1 or not isinstance(loop.body[0], ast.Expr):
            return node
        call_expr = loop.body[0].value
        if not isinstance(call_expr, ast.Call) or not isinstance(call_expr.func, ast.Attribute):
            return node
        if call_expr.func.attr != "write" or len(call_expr.args) != 1:
            return node

        file_ref = call_expr.func.value
        if not isinstance(file_ref, ast.Name):
            return node

        buffer_name = "_arwiz_buffer"
        init_buffer = ast.Assign(
            targets=[ast.Name(id=buffer_name, ctx=ast.Store())],
            value=ast.List(elts=[], ctx=ast.Load()),
        )
        append_stmt = ast.Expr(
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id=buffer_name, ctx=ast.Load()),
                    attr="append",
                    ctx=ast.Load(),
                ),
                args=[call_expr.args[0]],
                keywords=[],
            )
        )
        join_write = ast.Expr(
            value=ast.Call(
                func=ast.Attribute(value=file_ref, attr="write", ctx=ast.Load()),
                args=[
                    ast.Call(
                        func=ast.Attribute(
                            value=ast.Constant(value=""), attr="join", ctx=ast.Load()
                        ),
                        args=[ast.Name(id=buffer_name, ctx=ast.Load())],
                        keywords=[],
                    )
                ],
                keywords=[],
            )
        )

        loop.body = [append_stmt]
        node.body = [init_buffer, loop, join_write]
        return node


def apply_batch_io(source_code: str) -> str:
    tree = ast.parse(source_code)
    transformed = _BatchIOTransformer().visit(tree)
    ast.fix_missing_locations(transformed)
    return ast.unparse(transformed)


batch_io = apply_batch_io

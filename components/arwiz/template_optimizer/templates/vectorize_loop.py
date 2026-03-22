import ast


class _LoopVectorizer(ast.NodeTransformer):
    def __init__(self, numpy_name: str) -> None:
        self.needs_numpy = False
        self._numpy_name = numpy_name

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        self.generic_visit(node)
        new_body: list[ast.stmt] = []
        i = 0
        while i < len(node.body):
            stmt = node.body[i]
            if (
                i + 1 < len(node.body)
                and isinstance(stmt, ast.Assign)
                and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)
                and isinstance(stmt.value, ast.Constant)
                and stmt.value.value in {0}
                and isinstance(node.body[i + 1], ast.For)
            ):
                acc_name = stmt.targets[0].id
                for_stmt = node.body[i + 1]
                assert isinstance(for_stmt, ast.For)
                if (
                    len(for_stmt.body) == 1
                    and isinstance(for_stmt.body[0], ast.AugAssign)
                    and isinstance(for_stmt.body[0].target, ast.Name)
                    and for_stmt.body[0].target.id == acc_name
                    and isinstance(for_stmt.body[0].op, ast.Add)
                ):
                    self.needs_numpy = True
                    repl = ast.Assign(
                        targets=[ast.Name(id=acc_name, ctx=ast.Store())],
                        value=ast.Call(
                            func=ast.Attribute(
                                value=ast.Name(id=self._numpy_name, ctx=ast.Load()),
                                attr="sum",
                                ctx=ast.Load(),
                            ),
                            args=[
                                ast.Call(
                                    func=ast.Name(id="list", ctx=ast.Load()),
                                    args=[
                                        ast.GeneratorExp(
                                            elt=for_stmt.body[0].value,
                                            generators=[
                                                ast.comprehension(
                                                    target=for_stmt.target,
                                                    iter=for_stmt.iter,
                                                    ifs=[],
                                                    is_async=0,
                                                )
                                            ],
                                        )
                                    ],
                                    keywords=[],
                                )
                            ],
                            keywords=[],
                        ),
                    )
                    new_body.append(ast.fix_missing_locations(repl))
                    i += 2
                    continue

            if isinstance(stmt, ast.For) and len(stmt.body) == 1:
                loop_stmt = stmt.body[0]
                if (
                    isinstance(loop_stmt, ast.Expr)
                    and isinstance(loop_stmt.value, ast.Call)
                    and isinstance(loop_stmt.value.func, ast.Attribute)
                    and loop_stmt.value.func.attr == "append"
                    and len(loop_stmt.value.args) == 1
                    and not loop_stmt.value.keywords
                    and isinstance(loop_stmt.value.func.value, ast.Name)
                ):
                    result_name = loop_stmt.value.func.value.id
                    repl = ast.Assign(
                        targets=[ast.Name(id=result_name, ctx=ast.Store())],
                        value=ast.ListComp(
                            elt=loop_stmt.value.args[0],
                            generators=[
                                ast.comprehension(
                                    target=stmt.target,
                                    iter=stmt.iter,
                                    ifs=[],
                                    is_async=0,
                                )
                            ],
                        ),
                    )
                    new_body.append(ast.fix_missing_locations(repl))
                    i += 1
                    continue
            new_body.append(stmt)
            i += 1
        node.body = new_body
        return node


def _has_numpy_import(module: ast.Module) -> bool:
    return _get_numpy_namespace_name(module) is not None


def _get_numpy_namespace_name(module: ast.Module) -> str | None:
    for statement in module.body:
        if isinstance(statement, ast.Import):
            for alias in statement.names:
                if alias.name == "numpy":
                    return alias.asname or "numpy"
    return None


def apply_vectorize_loop(source_code: str) -> str:
    tree = ast.parse(source_code)
    if not isinstance(tree, ast.Module):
        return source_code

    numpy_name = _get_numpy_namespace_name(tree) or "np"
    transformer = _LoopVectorizer(numpy_name=numpy_name)
    transformed = transformer.visit(tree)
    if (
        transformer.needs_numpy
        and isinstance(transformed, ast.Module)
        and not _has_numpy_import(transformed)
    ):
        transformed.body.insert(0, ast.Import(names=[ast.alias(name="numpy", asname="np")]))
    ast.fix_missing_locations(transformed)
    return ast.unparse(transformed)


vectorize_loop = apply_vectorize_loop

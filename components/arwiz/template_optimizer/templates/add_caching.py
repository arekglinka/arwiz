import ast


def _is_lru_cache_decorator(decorator: ast.expr) -> bool:
    if isinstance(decorator, ast.Name):
        return decorator.id == "lru_cache"

    if isinstance(decorator, ast.Attribute):
        return decorator.attr == "lru_cache"

    if isinstance(decorator, ast.Call):
        return _is_lru_cache_decorator(decorator.func)

    return "lru_cache" in ast.unparse(decorator)


class _CachingAdder(ast.NodeTransformer):
    def __init__(self) -> None:
        self.modified = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        self.generic_visit(node)
        has_cache = any(_is_lru_cache_decorator(deco) for deco in node.decorator_list)
        if not has_cache:
            self.modified = True
            node.decorator_list.insert(
                0,
                ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id="functools", ctx=ast.Load()),
                        attr="lru_cache",
                        ctx=ast.Load(),
                    ),
                    args=[],
                    keywords=[ast.keyword(arg="maxsize", value=ast.Constant(value=None))],
                ),
            )
        return node


def _has_functools_import(tree: ast.Module) -> bool:
    for stmt in tree.body:
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                if alias.name == "functools":
                    return True
        if isinstance(stmt, ast.ImportFrom) and stmt.module == "functools":
            return True
    return False


def apply_add_caching(source_code: str) -> str:
    tree = ast.parse(source_code)
    transformer = _CachingAdder()
    transformed = transformer.visit(tree)
    if (
        transformer.modified
        and isinstance(transformed, ast.Module)
        and not _has_functools_import(transformed)
    ):
        transformed.body.insert(0, ast.Import(names=[ast.alias(name="functools", asname=None)]))
    ast.fix_missing_locations(transformed)
    return ast.unparse(transformed)


add_caching = apply_add_caching

import ast
import warnings

from .._shared import apply_transformer

_UNHASHABLE_HINTS = {"dict", "list", "set", "frozenset", "DataFrame"}


def _has_unhashable_params(node: ast.FunctionDef) -> bool:
    for arg in node.args.args:
        annotation = arg.annotation
        if annotation is None:
            continue
        if isinstance(annotation, ast.Name) and annotation.id in _UNHASHABLE_HINTS:
            return True
        if (
            isinstance(annotation, ast.Subscript)
            and isinstance(annotation.value, ast.Name)
            and annotation.value.id in _UNHASHABLE_HINTS
        ):
            return True
        if (
            isinstance(annotation, ast.Constant)
            and isinstance(annotation.value, str)
            and annotation.value in _UNHASHABLE_HINTS
        ):
            return True
    return False


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
            if _has_unhashable_params(node):
                warnings.warn(
                    f"[arwiz] Function '{node.name}' has parameters with "
                    "unhashable type annotations. @lru_cache may fail at "
                    "runtime for these parameter types.",
                    stacklevel=2,
                )
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


def apply_add_caching(source_code: str) -> str:
    return apply_transformer(
        source_code,
        _CachingAdder(),
        import_to_add="functools",
    )


add_caching = apply_add_caching

import ast

from .._shared import apply_transformer


def _is_jax_jit_decorator(decorator: ast.expr) -> bool:
    if isinstance(decorator, ast.Attribute) and isinstance(decorator.value, ast.Name):
        return decorator.value.id == "jax" and decorator.attr == "jit"

    if isinstance(decorator, ast.Name):
        return decorator.id == "jit"

    if isinstance(decorator, ast.Call):
        return _is_jax_jit_decorator(decorator.func)

    deco_text = ast.unparse(decorator)
    return "jax.jit" in deco_text or deco_text == "jit" or deco_text.endswith(".jit")


class _JaxTransformer(ast.NodeTransformer):
    def __init__(self) -> None:
        self.modified = False
        self._function_stack: list[bool] = []

    def visit_Import(self, node: ast.Import) -> ast.AST:
        replaced_aliases: list[ast.alias] = []
        replaced_any = False
        for alias in node.names:
            if alias.name == "numpy" and alias.asname == "np":
                replaced_aliases.append(ast.alias(name="jax.numpy", asname="jnp"))
                replaced_any = True
            else:
                replaced_aliases.append(alias)

        if replaced_any:
            self.modified = True
            return ast.Import(names=replaced_aliases)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        self._function_stack.append(False)
        self.generic_visit(node)
        uses_array_ops = self._function_stack.pop()

        if uses_array_ops and not any(_is_jax_jit_decorator(deco) for deco in node.decorator_list):
            node.decorator_list.insert(
                0,
                ast.Attribute(
                    value=ast.Name(id="jax", ctx=ast.Load()),
                    attr="jit",
                    ctx=ast.Load(),
                ),
            )
            self.modified = True
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        self._function_stack.append(False)
        self.generic_visit(node)
        self._function_stack.pop()
        return node

    def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
        self.generic_visit(node)
        if isinstance(node.value, ast.Name) and node.value.id == "np":
            node.value = ast.Name(id="jnp", ctx=ast.Load())
            if self._function_stack:
                self._function_stack[-1] = True
            self.modified = True
        return node


def apply_jax_optimize(source_code: str) -> str:
    return apply_transformer(
        source_code,
        _JaxTransformer(),
        import_to_add="jax",
    )

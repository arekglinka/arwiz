import ast

from .._shared import has_import


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


def apply_numba_jit(source_code: str) -> str:
    try:
        tree = ast.parse(source_code)
    except (SyntaxError, ValueError):
        return source_code
    transformer = _NumbaJITAdder()
    transformed = transformer.visit(tree)
    if (
        transformer.modified
        and isinstance(transformed, ast.Module)
        and not has_import(transformed, "numba")
    ):
        transformed.body.insert(0, ast.Import(names=[ast.alias(name="numba", asname=None)]))
    ast.fix_missing_locations(transformed)
    return ast.unparse(transformed)


add_numba_jit = apply_numba_jit


def _is_simple_iter_index(node: ast.expr, iter_name: str) -> bool:
    return isinstance(node, ast.Name) and node.id == iter_name


def _subscript_base_name(node: ast.Subscript) -> str | None:
    if isinstance(node.value, ast.Name):
        return node.value.id
    return None


class _ParallelLoopSafetyAnalyzer(ast.NodeVisitor):
    def __init__(self, iter_name: str) -> None:
        self.iter_name = iter_name
        self.safe = True

    def _mark_unsafe(self) -> None:
        self.safe = False

    def visit_For(self, node: ast.For) -> None:
        if node is None:
            return
        self._mark_unsafe()

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        if node is None:
            return
        self._mark_unsafe()

    def visit_While(self, node: ast.While) -> None:
        if node is None:
            return
        self._mark_unsafe()

    def visit_Break(self, node: ast.Break) -> None:
        if node is None:
            return
        self._mark_unsafe()

    def visit_Continue(self, node: ast.Continue) -> None:
        if node is None:
            return
        self._mark_unsafe()

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        if node is None:
            return
        self._mark_unsafe()

    def visit_Subscript(self, node: ast.Subscript) -> None:
        if isinstance(node.ctx, ast.Load) and not _is_simple_iter_index(node.slice, self.iter_name):
            self._mark_unsafe()
        self.generic_visit(node)


def _is_parallel_safe_loop(node: ast.For) -> bool:
    if not isinstance(node.target, ast.Name):
        return False

    iter_name = node.target.id
    analyzer = _ParallelLoopSafetyAnalyzer(iter_name)
    for stmt in node.body:
        analyzer.visit(stmt)
        if not analyzer.safe:
            return False

    for stmt in node.orelse:
        analyzer.visit(stmt)
        if not analyzer.safe:
            return False

    writes: dict[str, set[str]] = {}
    for stmt in node.body:
        if not isinstance(stmt, ast.Assign):
            continue
        for target in stmt.targets:
            if not isinstance(target, ast.Subscript):
                return False
            if not _is_simple_iter_index(target.slice, iter_name):
                return False
            base = _subscript_base_name(target)
            if base is None:
                return False
            key = ast.unparse(target.slice)
            writes.setdefault(base, set()).add(key)

    for stmt in node.body:
        for sub in ast.walk(stmt):
            if not isinstance(sub, ast.Subscript) or not isinstance(sub.ctx, ast.Load):
                continue
            base = _subscript_base_name(sub)
            if base is None:
                return False
            read_index = ast.unparse(sub.slice)
            if base in writes and any(idx != read_index for idx in writes[base]):
                return False

    return True


class _NumbaParallelTransformer(ast.NodeTransformer):
    def __init__(self) -> None:
        self.modified = False

    def _make_parallel_njit_decorator(self) -> ast.expr:
        return ast.Call(
            func=ast.Attribute(
                value=ast.Name(id="numba", ctx=ast.Load()),
                attr="njit",
                ctx=ast.Load(),
            ),
            args=[],
            keywords=[ast.keyword(arg="parallel", value=ast.Constant(value=True))],
        )

    def _ensure_parallel_njit(self, node: ast.FunctionDef) -> None:
        for index, decorator in enumerate(node.decorator_list):
            if not _is_numba_jit_decorator(decorator):
                continue

            if isinstance(decorator, ast.Call):
                has_parallel_kw = False
                for keyword in decorator.keywords:
                    if keyword.arg == "parallel":
                        has_parallel_kw = True
                        if (
                            not isinstance(keyword.value, ast.Constant)
                            or keyword.value.value is not True
                        ):
                            keyword.value = ast.Constant(value=True)
                            self.modified = True
                        break

                if not has_parallel_kw:
                    decorator.keywords.append(
                        ast.keyword(arg="parallel", value=ast.Constant(value=True))
                    )
                    self.modified = True

                if not (
                    isinstance(decorator.func, ast.Attribute)
                    and isinstance(decorator.func.value, ast.Name)
                    and decorator.func.value.id == "numba"
                    and decorator.func.attr == "njit"
                ):
                    decorator.func = ast.Attribute(
                        value=ast.Name(id="numba", ctx=ast.Load()),
                        attr="njit",
                        ctx=ast.Load(),
                    )
                    self.modified = True
                node.decorator_list[index] = decorator
                return

            node.decorator_list[index] = self._make_parallel_njit_decorator()
            self.modified = True
            return

        node.decorator_list.insert(0, self._make_parallel_njit_decorator())
        self.modified = True

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        self.generic_visit(node)
        self._ensure_parallel_njit(node)
        return node

    def visit_For(self, node: ast.For) -> ast.AST:
        self.generic_visit(node)
        if not _is_parallel_safe_loop(node):
            return node

        if (
            isinstance(node.iter, ast.Call)
            and isinstance(node.iter.func, ast.Name)
            and node.iter.func.id == "range"
        ):
            node.iter.func = ast.Attribute(
                value=ast.Name(id="numba", ctx=ast.Load()),
                attr="prange",
                ctx=ast.Load(),
            )
            self.modified = True
        return node


def has_parallel_safe_loop(source_code: str) -> bool:
    try:
        tree = ast.parse(source_code)
    except (SyntaxError, ValueError):
        return False
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.For)
            and _is_parallel_safe_loop(node)
            and isinstance(node.iter, ast.Call)
            and isinstance(node.iter.func, ast.Name)
            and node.iter.func.id == "range"
        ):
            return True
    return False


def apply_numba_parallel(source_code: str) -> str:
    try:
        tree = ast.parse(source_code)
    except (SyntaxError, ValueError):
        return source_code
    transformer = _NumbaParallelTransformer()
    transformed = transformer.visit(tree)
    if (
        transformer.modified
        and isinstance(transformed, ast.Module)
        and not has_import(transformed, "numba")
    ):
        transformed.body.insert(0, ast.Import(names=[ast.alias(name="numba", asname=None)]))
    ast.fix_missing_locations(transformed)
    return ast.unparse(transformed)

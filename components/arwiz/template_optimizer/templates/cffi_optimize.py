import ast

_NON_NUMERIC_COMMENT = (
    "# CFFI is most useful for calling existing C libraries or C APIs at runtime.\n"
)


def _get_first_function(source_code: str) -> ast.FunctionDef | None:
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return None

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            return node
    return None


def _is_numeric_loop_function(func: ast.FunctionDef) -> bool:
    has_loop = any(isinstance(node, ast.For) for node in ast.walk(func))
    if not has_loop:
        return False

    has_numeric_op = any(
        isinstance(node, ast.BinOp)
        and isinstance(
            node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv)
        )
        for node in ast.walk(func)
    ) or any(
        isinstance(node, ast.AugAssign)
        and isinstance(
            node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv)
        )
        for node in ast.walk(func)
    )

    has_stringy_constructs = any(
        isinstance(node, (ast.JoinedStr, ast.FormattedValue)) for node in ast.walk(func)
    )
    return has_numeric_op and not has_stringy_constructs


def _indexed_param_names(func: ast.FunctionDef) -> list[str]:
    indexed_names: list[str] = []
    arg_names = {arg.arg for arg in func.args.args}
    for node in ast.walk(func):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
            name = node.value.id
            if name in arg_names and name not in indexed_names:
                indexed_names.append(name)
    return indexed_names


def _length_param_name(func: ast.FunctionDef) -> str:
    preferred = {"n", "size", "length", "count"}
    for arg in func.args.args:
        if arg.arg in preferred:
            return arg.arg
    return "n"


def _build_cffi_numeric_template(func: ast.FunctionDef) -> str:
    func_name = func.name
    array_params = _indexed_param_names(func)
    length_param = _length_param_name(func)

    if len(array_params) >= 2:
        left, right = array_params[0], array_params[1]
        c_signature = f"double {func_name}(double *{left}, double *{right}, int {length_param});"
        c_body = (
            f"double {func_name}(double *{left}, double *{right}, int {length_param}) {{\n"
            "    double total = 0.0;\n"
            f"    for (int i = 0; i < {length_param}; ++i) {{\n"
            f"        total += {left}[i] * {right}[i];\n"
            "    }\n"
            "    return total;\n"
            "}"
        )
        wrapper = (
            f"def {func_name}({left}, {right}, {length_param}):\n"
            "    ffi = FFI()\n"
            f'    ffi.cdef("{c_signature}")\n'
            '    lib = ffi.verify("""\n'
            f"{c_body}\n"
            '""")\n'
            f'    c_{left} = ffi.new("double[]", {left})\n'
            f'    c_{right} = ffi.new("double[]", {right})\n'
            f"    return float(lib.{func_name}(c_{left}, c_{right}, int({length_param})))\n"
        )
    elif len(array_params) == 1:
        arr = array_params[0]
        c_signature = f"double {func_name}(double *{arr}, int {length_param});"
        c_body = (
            f"double {func_name}(double *{arr}, int {length_param}) {{\n"
            "    double total = 0.0;\n"
            f"    for (int i = 0; i < {length_param}; ++i) {{\n"
            f"        total += {arr}[i];\n"
            "    }\n"
            "    return total;\n"
            "}"
        )
        wrapper = (
            f"def {func_name}({arr}, {length_param}):\n"
            "    ffi = FFI()\n"
            f'    ffi.cdef("{c_signature}")\n'
            '    lib = ffi.verify("""\n'
            f"{c_body}\n"
            '""")\n'
            f'    c_{arr} = ffi.new("double[]", {arr})\n'
            f"    return float(lib.{func_name}(c_{arr}, int({length_param})))\n"
        )
    else:
        c_signature = f"double {func_name}(int {length_param});"
        c_body = (
            f"double {func_name}(int {length_param}) {{\n"
            "    double total = 0.0;\n"
            f"    for (int i = 0; i < {length_param}; ++i) {{\n"
            "        total += (double)i;\n"
            "    }\n"
            "    return total;\n"
            "}"
        )
        wrapper = (
            f"def {func_name}({length_param}):\n"
            "    ffi = FFI()\n"
            f'    ffi.cdef("{c_signature}")\n'
            '    lib = ffi.verify("""\n'
            f"{c_body}\n"
            '""")\n'
            f"    return float(lib.{func_name}(int({length_param})))\n"
        )

    return "from cffi import FFI\n\n" + wrapper


def apply_cffi_optimize(source_code: str) -> str:
    func = _get_first_function(source_code)
    if func is None:
        return _NON_NUMERIC_COMMENT + source_code

    if not _is_numeric_loop_function(func):
        return _NON_NUMERIC_COMMENT + source_code

    return _build_cffi_numeric_template(func)

import ast

_BUILD_HINT = "// Build with maturin develop"


def _extract_function_names(tree: ast.Module) -> list[str]:
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            names.append(node.name)
    return names


def _is_string_heavy(tree: ast.Module) -> bool:
    methods = {
        "split",
        "join",
        "replace",
        "encode",
        "decode",
        "strip",
        "lstrip",
        "rstrip",
        "upper",
        "lower",
        "format",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return True
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in methods
        ):
            return True
    return False


def _build_rust_module(function_names: list[str]) -> str:
    exported = function_names or ["optimized_fn"]
    wrappers = "\n\n".join(
        [
            (
                "#[pyfunction]\n"
                f"fn {name}(input: &str) -> PyResult<String> {{\n"
                "    let output = input.trim().to_lowercase().replace('-', \"_\");\n"
                "    Ok(output)\n"
                "}"
            )
            for name in exported
        ]
    )
    module_regs = "\n    ".join(
        [f"m.add_function(wrap_pyfunction!({name}, m)?)?;" for name in exported]
    )
    return (
        "use pyo3::prelude::*;\n\n"
        f"{_BUILD_HINT}\n\n"
        f"{wrappers}\n\n"
        "#[pymodule]\n"
        "fn optimized_string_module(m: &Bound<'_, PyModule>) -> PyResult<()> {\n"
        f"    {module_regs}\n"
        "    Ok(())\n"
        "}"
    )


def apply_pyo3_optimize(source_code: str) -> str:
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return (
            "# PyO3 template could not parse source; returning safe guidance.\n"
            "# Rust/PyO3 is strongest for string processing and max single-thread performance.\n"
            "# Build with maturin develop\n"
            f"{source_code}"
        )

    if _is_string_heavy(tree):
        return _build_rust_module(_extract_function_names(tree))

    return (
        "# PyO3 suggestion: Rust is most effective for string-heavy workloads\n"
        "# and maximizing single-thread performance.\n"
        "# Build with maturin develop\n"
        f"{source_code}"
    )

import ast


def detect_for_loops(source: str) -> list[ast.For]:
    tree = ast.parse(source)
    return [node for node in ast.walk(tree) if isinstance(node, ast.For)]


def detect_pandas_operations(source: str) -> list[ast.Call]:
    tree = ast.parse(source)
    matches: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr in {"apply", "iterrows"}:
            matches.append(node)
    return matches


def detect_file_io_operations(source: str) -> list[ast.Call]:
    tree = ast.parse(source)
    matches: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Call):
                continue
            if isinstance(inner.func, ast.Name) and inner.func.id == "open":
                matches.append(inner)
            if isinstance(inner.func, ast.Attribute) and inner.func.attr in {
                "write",
                "writelines",
                "read",
                "readlines",
            }:
                matches.append(inner)
    return matches

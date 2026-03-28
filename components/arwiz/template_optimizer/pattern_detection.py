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


def detect_data_types(source: str) -> dict[str, str]:
    tree = ast.parse(source)
    inferred: dict[str, str] = {}

    annotation_map = {
        "float": "float",
        "int": "int",
        "str": "str",
        "list": "list",
        "dict": "dict",
        "ndarray": "ndarray",
    }

    ndarray_constructors = {
        "zeros",
        "ones",
        "array",
        "zeros_like",
        "ones_like",
        "empty",
        "empty_like",
    }

    def _annotation_to_type(annotation: ast.expr) -> str | None:
        if isinstance(annotation, ast.Name):
            return annotation_map.get(annotation.id)
        if isinstance(annotation, ast.Subscript) and isinstance(annotation.value, ast.Name):
            return annotation_map.get(annotation.value.id)
        if isinstance(annotation, ast.Attribute) and annotation.attr == "ndarray":
            return "ndarray"
        return None

    def _value_to_type(value: ast.expr) -> str | None:
        if isinstance(value, ast.Constant):
            if isinstance(value.value, float):
                return "float"
            if isinstance(value.value, int):
                return "int"
            if isinstance(value.value, str):
                return "str"
        if isinstance(value, ast.List):
            return "list"
        if isinstance(value, ast.Dict):
            return "dict"
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Attribute)
            and isinstance(value.func.value, ast.Name)
            and value.func.value.id in {"np", "numpy"}
            and value.func.attr in ndarray_constructors
        ):
            return "ndarray"
        return None

    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            annotated = _annotation_to_type(node.annotation)
            if annotated is not None:
                inferred[node.target.id] = annotated
                continue
            if node.value is not None:
                from_value = _value_to_type(node.value)
                if from_value is not None:
                    inferred[node.target.id] = from_value
        if isinstance(node, ast.Assign):
            from_value = _value_to_type(node.value)
            if from_value is None:
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    inferred[target.id] = from_value

    return inferred


def detect_array_operations(source: str) -> list[ast.Call]:
    tree = ast.parse(source)
    matches: list[ast.Call] = []

    operations = {
        "zeros",
        "ones",
        "array",
        "dot",
        "cross",
        "matmul",
        "einsum",
        "vstack",
        "hstack",
        "reshape",
        "transpose",
        "linspace",
        "arange",
        "sort",
        "argsort",
        "sum",
        "mean",
        "std",
        "min",
        "max",
        "sqrt",
        "abs",
        "zeros_like",
        "ones_like",
        "empty",
        "empty_like",
    }

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in operations:
            continue
        if isinstance(node.func.value, ast.Name) and node.func.value.id in {"np", "numpy"}:
            matches.append(node)

    return matches


def detect_control_flow_complexity(source: str) -> dict[str, int | bool]:
    tree = ast.parse(source)
    loop_count = 0

    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.While)):
            loop_count += 1

    def _walk_with_context(node: ast.AST, loop_depth: int = 0) -> tuple[int, int]:
        max_depth = loop_depth
        branch_count = 0
        if isinstance(node, (ast.For, ast.While)):
            loop_depth += 1
            max_depth = max(max_depth, loop_depth)
            for stmt in node.body:
                child_depth, child_branches = _walk_with_context(stmt, loop_depth)
                max_depth = max(max_depth, child_depth)
                branch_count += child_branches
            for stmt in node.orelse:
                child_depth, child_branches = _walk_with_context(stmt, loop_depth)
                max_depth = max(max_depth, child_depth)
                branch_count += child_branches
            return max_depth, branch_count

        if isinstance(node, ast.If) and loop_depth > 0:
            branch_count += 1

        for child in ast.iter_child_nodes(node):
            child_depth, child_branches = _walk_with_context(child, loop_depth)
            max_depth = max(max_depth, child_depth)
            branch_count += child_branches

        return max_depth, branch_count

    nesting_depth, branch_count_in_loops = _walk_with_context(tree)

    return {
        "loop_count": loop_count,
        "nesting_depth": nesting_depth,
        "branch_count_in_loops": branch_count_in_loops,
        "has_nested_loops": nesting_depth > 1,
    }


def detect_string_operations(source: str) -> list[ast.Call]:
    tree = ast.parse(source)
    matches: list[ast.Call] = []

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
        "capitalize",
        "title",
        "startswith",
        "endswith",
        "format",
        "count",
        "find",
        "rfind",
    }

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute) and node.func.attr in methods:
            matches.append(node)
            continue
        if isinstance(node.func, ast.Name) and node.func.id == "str":
            matches.append(node)

    return matches


def detect_memory_access_patterns(source: str) -> list[str]:
    tree = ast.parse(source)
    patterns: list[str] = []

    sequential_names = {"i", "j", "k", "idx", "index", "n"}

    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue

        slice_node = node.slice
        if isinstance(slice_node, ast.Slice) and slice_node.step is not None:
            if "strided" not in patterns:
                patterns.append("strided")
            continue

        if isinstance(slice_node, ast.Name):
            if slice_node.id in sequential_names:
                if "sequential" not in patterns:
                    patterns.append("sequential")
            elif "random_access" not in patterns:
                patterns.append("random_access")
            continue

        if not isinstance(slice_node, ast.Tuple) and "random_access" not in patterns:
            patterns.append("random_access")

    return patterns

import ast
from importlib import import_module


def _import(name: str):
    return import_module(name)


def test_detect_data_types_infers_supported_types() -> None:
    mod = _import("arwiz.template_optimizer.pattern_detection")
    source = """
x: float = 0.0
y: int
name: str = "alice"
arr = np.zeros(10)
arr2 = numpy.array([1, 2, 3])
items = [1, 2, 3]
mapping = {"a": 1}
"""
    inferred = mod.detect_data_types(source)
    assert inferred == {
        "x": "float",
        "y": "int",
        "name": "str",
        "arr": "ndarray",
        "arr2": "ndarray",
        "items": "list",
        "mapping": "dict",
    }


def test_detect_data_types_returns_empty_dict_when_unknown() -> None:
    mod = _import("arwiz.template_optimizer.pattern_detection")
    source = """
value = compute()
other = something_else(value)
"""
    assert mod.detect_data_types(source) == {}


def test_detect_array_operations_finds_numpy_calls_only() -> None:
    mod = _import("arwiz.template_optimizer.pattern_detection")
    source = """
a = np.zeros(10)
b = numpy.ones((2, 2))
c = np.zeros_like(a)
d = np.empty_like(a)
e = np.reshape(a, (2, 5))
f = scipy.zeros(10)
g = sum([1, 2, 3])
"""
    matches = mod.detect_array_operations(source)
    assert all(isinstance(call, ast.Call) for call in matches)
    attrs = {call.func.attr for call in matches if isinstance(call.func, ast.Attribute)}
    assert attrs == {"zeros", "ones", "zeros_like", "empty_like", "reshape"}


def test_detect_control_flow_complexity_reports_expected_metrics() -> None:
    mod = _import("arwiz.template_optimizer.pattern_detection")
    source = """
for i in range(n):
    if i % 2:
        continue
    while i < n:
        for j in range(m):
            if j > 0:
                break
"""
    complexity = mod.detect_control_flow_complexity(source)
    assert complexity == {
        "loop_count": 3,
        "nesting_depth": 3,
        "branch_count_in_loops": 2,
        "has_nested_loops": True,
    }


def test_detect_control_flow_complexity_empty_source() -> None:
    mod = _import("arwiz.template_optimizer.pattern_detection")
    source = """
if condition:
    x = 1
"""
    assert mod.detect_control_flow_complexity(source) == {
        "loop_count": 0,
        "nesting_depth": 0,
        "branch_count_in_loops": 0,
        "has_nested_loops": False,
    }


def test_detect_string_operations_finds_methods_and_constructor() -> None:
    mod = _import("arwiz.template_optimizer.pattern_detection")
    source = """
parts = value.split(",")
joined = "-".join(parts)
clean = value.strip().upper()
text = str(123)
"""
    matches = mod.detect_string_operations(source)
    assert all(isinstance(call, ast.Call) for call in matches)
    attrs = {call.func.attr for call in matches if isinstance(call.func, ast.Attribute)}
    assert {"split", "join", "strip", "upper"}.issubset(attrs)
    assert any(isinstance(call.func, ast.Name) and call.func.id == "str" for call in matches)


def test_detect_memory_access_patterns_identifies_all_supported_patterns() -> None:
    mod = _import("arwiz.template_optimizer.pattern_detection")
    source = """
x = a[i]
y = a[key]
z = a[1:10:2]
"""
    patterns = mod.detect_memory_access_patterns(source)
    assert set(patterns) == {"sequential", "random_access", "strided"}


def test_detect_memory_access_patterns_empty_when_no_subscript() -> None:
    mod = _import("arwiz.template_optimizer.pattern_detection")
    source = """
value = 1 + 2
"""
    assert mod.detect_memory_access_patterns(source) == []

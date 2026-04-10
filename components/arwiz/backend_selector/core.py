import ast
from importlib import import_module
from typing import Any


class DefaultBackendSelector:
    def __init__(self) -> None:
        self._manifest_cls = import_module("arwiz.backend_selector.manifest").BackendManifest
        self._manifest = self._manifest_cls()
        pattern_detection = import_module("arwiz.template_optimizer.pattern_detection")
        self._detect_for_loops = pattern_detection.detect_for_loops
        self._detect_data_types = pattern_detection.detect_data_types
        self._detect_array_operations = pattern_detection.detect_array_operations
        self._detect_control_flow_complexity = pattern_detection.detect_control_flow_complexity
        self._detect_string_operations = pattern_detection.detect_string_operations
        self._detect_memory_access_patterns = pattern_detection.detect_memory_access_patterns
        numba_jit_mod = import_module("arwiz.template_optimizer.templates.numba_jit")
        self._has_parallel_safe_loop = numba_jit_mod.has_parallel_safe_loop

    def _is_pure_numpy_vectorized(
        self,
        source_code: str,
        has_loops: bool,
        has_array_ops: bool,
        tree: ast.Module | None = None,
    ) -> bool:
        if has_loops or not has_array_ops:
            return False

        if tree is None:
            tree = ast.parse(source_code)
        _all_safe_np_calls = {
            "dot",
            "sum",
            "mean",
            "std",
            "min",
            "max",
            "sqrt",
            "abs",
            "matmul",
            "einsum",
            "transpose",
            "reshape",
            "vstack",
            "hstack",
            "sort",
            "argsort",
            "cross",
            "array",
            "zeros",
            "ones",
            "arange",
            "linspace",
            "full",
            "empty",
            "where",
            "clip",
            "astype",
            "conj",
            "real",
            "imag",
        }

        safe_builtins = {
            "len",
            "print",
            "range",
            "int",
            "float",
            "enumerate",
            "zip",
            "list",
            "dict",
            "set",
            "tuple",
            "str",
            "bool",
            "any",
            "all",
            "round",
            "abs",
            "pow",
            "max",
            "min",
            "isinstance",
            "type",
            "repr",
        }

        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        if not calls:
            return False

        for call in calls:
            func = call.func
            if isinstance(func, ast.Attribute):
                if (
                    isinstance(func.value, ast.Name)
                    and func.value.id in {"np", "numpy"}
                    and func.attr in _all_safe_np_calls
                ):
                    continue
                return False
            if isinstance(func, ast.Name) and func.id in safe_builtins:
                continue
            return False
        return True

    def _heuristic_ranking(self, source_code: str) -> list[tuple[str, float]]:
        tree = ast.parse(source_code)

        has_loops = bool(self._detect_for_loops(source_code, tree=tree))
        has_array_ops = bool(self._detect_array_operations(source_code, tree=tree))
        has_string_ops = bool(self._detect_string_operations(source_code, tree=tree))

        if not has_string_ops and self._is_pure_numpy_vectorized(
            source_code, has_loops, has_array_ops, tree=tree
        ):
            return []

        score_map: dict[str, float] = {}

        def _recommend(backends: list[str], confidence: float) -> None:
            for backend in backends:
                score_map[backend] = max(score_map.get(backend, 0.0), confidence)

        if has_string_ops:
            _recommend(["pyo3"], 0.9)

        data_types = self._detect_data_types(source_code, tree=tree)
        if any(dtype == "ndarray" for dtype in data_types.values()):
            _recommend(["numba", "cython"], 0.7)

        control_flow = self._detect_control_flow_complexity(source_code, tree=tree)
        if bool(control_flow.get("has_nested_loops")):
            _recommend(["cython", "numba"], 0.7)

        if has_loops and self._has_parallel_safe_loop(source_code):
            _recommend(["numba_parallel"], 0.75)

        if has_array_ops and not has_loops:
            _recommend(["jax", "cupy"], 0.6)

        memory_patterns = self._detect_memory_access_patterns(source_code, tree=tree)

        # Arithmetic on array elements in loops → numexpr
        has_arithmetic_ops = any(op in source_code for op in ("+", "-", "*", "/", "**"))
        if (
            has_loops
            and "sequential" in memory_patterns
            and has_arithmetic_ops
            and not has_array_ops
        ):
            _recommend(["numexpr"], 0.5)

        # Indexed arithmetic in loops → cffi (lower confidence than numexpr, more setup)
        if (
            has_loops
            and "sequential" in memory_patterns
            and has_arithmetic_ops
            and not has_string_ops
        ):
            _recommend(["cffi"], 0.4)

        if "strided" in memory_patterns:
            _recommend(["cython"], 0.6)

        if not score_map:
            return []

        preferred_order = {
            "pyo3": 0,
            "cython": 1,
            "numba": 2,
            "numba_parallel": 3,
            "jax": 4,
            "cupy": 5,
            "numexpr": 6,
            "cffi": 7,
            "taichi": 8,
        }

        ranked = sorted(
            score_map.items(),
            key=lambda item: (-item[1], preferred_order.get(item[0], 99), item[0]),
        )
        return [(name, float(score)) for name, score in ranked]

    def select_backends(
        self,
        source_code: str,
        hotspot: Any = None,
    ) -> list[str]:
        if hotspot is not None and not source_code:
            return []
        try:
            ranked = self._heuristic_ranking(source_code)
        except SyntaxError:
            return []

        selected: list[str] = []
        for name, _ in ranked:
            if self.is_backend_available(name):
                selected.append(name)
        return selected

    def get_manifest(self) -> dict[str, Any]:
        return self._manifest.all_backends()

    def is_backend_available(self, name: str) -> bool:
        is_available, _ = self._manifest.check_availability(name)
        return is_available

    def rank_backends(
        self,
        source_code: str,
        hotspot: Any = None,
    ) -> list[tuple[str, float]]:
        if hotspot is not None and not source_code:
            return []
        try:
            ranked = self._heuristic_ranking(source_code)
        except SyntaxError:
            return []

        return [(name, score) for name, score in ranked if self.is_backend_available(name)]

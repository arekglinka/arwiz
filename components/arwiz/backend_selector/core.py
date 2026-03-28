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

    def _is_pure_numpy_vectorized(
        self,
        source_code: str,
        has_loops: bool,
        has_array_ops: bool,
    ) -> bool:
        if has_loops or not has_array_ops:
            return False

        ast_mod = import_module("ast")
        tree = ast_mod.parse(source_code)
        vectorized_only_ops = {
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
        }

        calls = [node for node in ast_mod.walk(tree) if isinstance(node, ast_mod.Call)]
        if not calls:
            return False

        for call in calls:
            func = call.func
            if isinstance(func, ast_mod.Attribute):
                if (
                    isinstance(func.value, ast_mod.Name)
                    and func.value.id in {"np", "numpy"}
                    and func.attr in vectorized_only_ops
                ):
                    continue
                return False
            if isinstance(func, ast_mod.Name) and func.id in {"len"}:
                continue
            return False
        return True

    def _heuristic_ranking(self, source_code: str) -> list[tuple[str, float]]:
        has_loops = bool(self._detect_for_loops(source_code))
        has_array_ops = bool(self._detect_array_operations(source_code))
        has_string_ops = bool(self._detect_string_operations(source_code))

        if not has_string_ops and has_loops and has_array_ops:
            return []

        if not has_string_ops and self._is_pure_numpy_vectorized(
            source_code, has_loops, has_array_ops
        ):
            return []

        score_map: dict[str, float] = {}

        def _recommend(backends: list[str], confidence: float) -> None:
            for backend in backends:
                score_map[backend] = max(score_map.get(backend, 0.0), confidence)

        if has_string_ops:
            _recommend(["pyo3"], 0.9)

        data_types = self._detect_data_types(source_code)
        if any(dtype == "ndarray" for dtype in data_types.values()):
            _recommend(["numba", "cython"], 0.7)

        control_flow = self._detect_control_flow_complexity(source_code)
        if bool(control_flow.get("has_nested_loops")):
            _recommend(["cython", "numba"], 0.7)

        if has_array_ops and not has_loops:
            _recommend(["jax", "cupy"], 0.6)

        memory_patterns = self._detect_memory_access_patterns(source_code)

        # Arithmetic on array elements in loops → numexpr
        has_arithmetic_ops = any(op in source_code for op in ("+", "-", "*", "/", "**"))
        if (
            has_loops
            and "sequential" in memory_patterns
            and has_arithmetic_ops
            and not has_array_ops
        ):
            _recommend(["numexpr"], 0.5)

        if "strided" in memory_patterns:
            _recommend(["cython"], 0.6)

        if not score_map:
            return []

        preferred_order = {
            "pyo3": 0,
            "cython": 1,
            "numba": 2,
            "jax": 3,
            "cupy": 4,
            "numexpr": 5,
            "cffi": 6,
            "taichi": 7,
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

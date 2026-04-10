import ast
from collections.abc import Callable

from ..foundation import HotSpot
from .pattern_detection import (
    detect_file_io_operations,
    detect_for_loops,
    detect_pandas_operations,
    detect_string_operations,
)
from .templates import (
    apply_add_caching,
    apply_batch_io,
    apply_cffi_optimize,
    apply_cupy_optimize,
    apply_cython_optimize,
    apply_jax_optimize,
    apply_numba_jit,
    apply_numba_parallel,
    apply_numexpr_optimize,
    apply_pyo3_optimize,
    apply_taichi_optimize,
    apply_vectorize_loop,
)
from .templates.numba_jit import has_parallel_safe_loop


class DefaultTemplateOptimizer:
    _templates: dict[str, Callable[[str], str]]

    def __init__(self) -> None:
        self._templates = {
            "vectorize_loop": apply_vectorize_loop,
            "numba_jit": apply_numba_jit,
            "numba_parallel": apply_numba_parallel,
            "cython_optimize": apply_cython_optimize,
            "add_caching": apply_add_caching,
            "batch_io": apply_batch_io,
            "cffi_optimize": apply_cffi_optimize,
            "numexpr_optimize": apply_numexpr_optimize,
            "jax_optimize": apply_jax_optimize,
            "cupy_optimize": apply_cupy_optimize,
            "pyo3_optimize": apply_pyo3_optimize,
            "taichi_optimize": apply_taichi_optimize,
        }

    def apply_template(self, source_code: str, template_name: str) -> str:
        if template_name not in self._templates:
            msg = f"Unknown template: {template_name}"
            raise ValueError(msg)
        return self._templates[template_name](source_code)

    def list_templates(self) -> list[str]:
        return list(self._templates.keys())

    def detect_applicable_templates(
        self,
        source_code: str,
        hotspot: HotSpot | None = None,
    ) -> list[str]:
        try:
            tree = ast.parse(source_code)
        except (SyntaxError, ValueError):
            return []

        detected: list[str] = []
        loops = detect_for_loops(source_code, tree=tree)
        has_array_indexing = "[" in source_code and "]" in source_code
        has_arithmetic = any(op in source_code for op in ["+", "-", "*", "/", "**"])
        if loops:
            detected.append("vectorize_loop")
            detected.append("numba_jit")
            if has_parallel_safe_loop(source_code):
                detected.append("numba_parallel")
            if has_array_indexing:
                detected.append("cython_optimize")
            if has_array_indexing and has_arithmetic:
                detected.append("numexpr_optimize")
                detected.append("cffi_optimize")
        if detect_file_io_operations(source_code, tree=tree):
            detected.append("batch_io")
        if detect_pandas_operations(source_code, tree=tree) and "vectorize_loop" not in detected:
            detected.append("vectorize_loop")
        if detect_string_operations(source_code, tree=tree):
            detected.append("pyo3_optimize")

        if "import numpy as np" in source_code and "np." in source_code:
            detected.append("jax_optimize")
            detected.append("cupy_optimize")

        if hotspot is not None and hotspot.call_count > 1:
            detected.append("add_caching")

        return list(dict.fromkeys(detected))

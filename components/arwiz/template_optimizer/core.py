from collections.abc import Callable

from arwiz.foundation import HotSpot
from arwiz.template_optimizer.pattern_detection import (
    detect_file_io_operations,
    detect_for_loops,
    detect_pandas_operations,
)
from arwiz.template_optimizer.templates import (
    apply_add_caching,
    apply_batch_io,
    apply_numba_jit,
    apply_vectorize_loop,
)


class DefaultTemplateOptimizer:
    _templates: dict[str, Callable[[str], str]]

    def __init__(self) -> None:
        self._templates = {
            "vectorize_loop": apply_vectorize_loop,
            "numba_jit": apply_numba_jit,
            "add_caching": apply_add_caching,
            "batch_io": apply_batch_io,
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
        detected: list[str] = []
        if detect_for_loops(source_code):
            detected.append("vectorize_loop")
            detected.append("numba_jit")
        if detect_file_io_operations(source_code):
            detected.append("batch_io")
        if detect_pandas_operations(source_code) and "vectorize_loop" not in detected:
            detected.append("vectorize_loop")

        if hotspot is not None and hotspot.call_count > 1:
            detected.append("add_caching")

        unique: list[str] = []
        for name in detected:
            if name not in unique:
                unique.append(name)
        return unique

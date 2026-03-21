from typing import Any, Protocol


class EquivalenceCheckerProtocol(Protocol):
    def check_equivalence(
        self, original: Any, optimized: Any, tolerance: float = 1e-6
    ) -> tuple[bool, str]: ...
    def compare_outputs(
        self, original: Any, optimized: Any, tolerance: float = 1e-6
    ) -> dict[str, Any]: ...

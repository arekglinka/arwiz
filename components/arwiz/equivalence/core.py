from __future__ import annotations

from typing import Any

from arwiz.equivalence.tolerance import deep_equal


class DefaultEquivalenceChecker:
    def check_equivalence(
        self, original: Any, optimized: Any, tolerance: float = 1e-6
    ) -> tuple[bool, str]:
        return deep_equal(original, optimized, tolerance)

    def compare_outputs(
        self, original: Any, optimized: Any, tolerance: float = 1e-6
    ) -> dict[str, Any]:
        equivalent, reason = deep_equal(original, optimized, tolerance)
        return {
            "equivalent": equivalent,
            "reason": reason,
            "original_type": type(original).__name__,
            "optimized_type": type(optimized).__name__,
        }

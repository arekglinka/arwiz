from __future__ import annotations

import math
from typing import Any

import numpy as np

__all__ = ["is_close", "arrays_close", "deep_equal"]


def is_close(a: Any, b: Any, tolerance: float = 1e-6) -> bool:
    if isinstance(a, float) and isinstance(b, float):
        if math.isnan(a) and math.isnan(b):
            return True
        if math.isnan(a) or math.isnan(b):
            return False
        if math.isinf(a) or math.isinf(b):
            return a == b
        return abs(a - b) <= tolerance

    if isinstance(a, (np.floating, np.integer)) or isinstance(b, (np.floating, np.integer)):
        a_f, b_f = float(a), float(b)
        return is_close(a_f, b_f, tolerance)

    return a == b


def arrays_close(a: Any, b: Any, tolerance: float = 1e-6) -> tuple[bool, str]:
    if not isinstance(a, np.ndarray) or not isinstance(b, np.ndarray):
        return False, "One or both arguments are not numpy arrays"

    if a.shape != b.shape:
        return False, f"Shape mismatch: {a.shape} vs {b.shape}"

    if np.array_equal(a, b):
        return True, "Arrays are exactly equal"

    nan_mask_a = np.isnan(a)
    nan_mask_b = np.isnan(b)
    if not np.array_equal(nan_mask_a, nan_mask_b):
        return False, "NaN positions differ"

    if np.all(nan_mask_a & nan_mask_b) and nan_mask_a.all():
        return True, "Both arrays are all NaN"

    non_nan_mask = ~(nan_mask_a | nan_mask_b)
    if not non_nan_mask.any():
        return True, "All elements are NaN"

    if np.allclose(a[non_nan_mask], b[non_nan_mask], atol=tolerance):
        return True, "Arrays are close within tolerance"

    max_diff = float(np.nanmax(np.abs(a.astype(float) - b.astype(float))))
    return False, f"Arrays differ (max diff: {max_diff})"


def deep_equal(a: Any, b: Any, tolerance: float = 1e-6) -> tuple[bool, str]:
    return _deep_equal(a, b, tolerance, set())


def _deep_equal(a: Any, b: Any, tolerance: float, visited: set[int]) -> tuple[bool, str]:
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        return arrays_close(a, b, tolerance)

    if isinstance(a, float) and isinstance(b, float):
        if is_close(a, b, tolerance):
            return True, "Values are equal within tolerance"
        return False, f"Floats differ: {a} vs {b}"

    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if is_close(a, b, tolerance):
            return True, "Values are equal within tolerance"
        return False, f"Values differ: {a} vs {b}"

    if a is None and b is None:
        return True, "Both None"
    if a is None or b is None:
        return False, f"None vs non-None: {a!r} vs {b!r}"

    if isinstance(a, dict) and isinstance(b, dict):
        if id(a) in visited or id(b) in visited:
            return True, "circular reference detected (assumed equivalent)"
        visited.add(id(a))
        visited.add(id(b))
        try:
            if set(a.keys()) != set(b.keys()):
                return False, (f"Dict keys differ: {set(a.keys())} vs {set(b.keys())}")
            for k in a:
                eq, reason = _deep_equal(a[k], b[k], tolerance, visited)
                if not eq:
                    return False, f"Dict key '{k}': {reason}"
            return True, "Dicts are equivalent"
        finally:
            visited.discard(id(a))
            visited.discard(id(b))

    if isinstance(a, list) and isinstance(b, list):
        if id(a) in visited or id(b) in visited:
            return True, "circular reference detected (assumed equivalent)"
        visited.add(id(a))
        visited.add(id(b))
        try:
            if len(a) != len(b):
                return False, f"List length mismatch: {len(a)} vs {len(b)}"
            for i, (ea, eb) in enumerate(zip(a, b, strict=False)):
                eq, reason = _deep_equal(ea, eb, tolerance, visited)
                if not eq:
                    return False, f"List index {i}: {reason}"
            return True, "Lists are equivalent"
        finally:
            visited.discard(id(a))
            visited.discard(id(b))

    if isinstance(a, tuple) and isinstance(b, tuple):
        if id(a) in visited or id(b) in visited:
            return True, "circular reference detected (assumed equivalent)"
        visited.add(id(a))
        visited.add(id(b))
        try:
            if len(a) != len(b):
                return False, f"Tuple length mismatch: {len(a)} vs {len(b)}"
            for i, (ea, eb) in enumerate(zip(a, b, strict=False)):
                eq, reason = _deep_equal(ea, eb, tolerance, visited)
                if not eq:
                    return False, f"Tuple index {i}: {reason}"
            return True, "Tuples are equivalent"
        finally:
            visited.discard(id(a))
            visited.discard(id(b))

    if isinstance(a, set) and isinstance(b, set):
        if id(a) in visited or id(b) in visited:
            return True, "circular reference detected (assumed equivalent)"
        visited.add(id(a))
        visited.add(id(b))
        try:
            if a == b:
                return True, "Sets are equal"
            return False, f"Sets differ: {a} vs {b}"
        finally:
            visited.discard(id(a))
            visited.discard(id(b))

    if type(a) is type(b) and a == b:
        return True, f"Values equal: {a!r}"

    return False, f"Type/value mismatch: {type(a).__name__}({a!r}) vs {type(b).__name__}({b!r})"

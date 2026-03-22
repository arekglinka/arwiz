"""Tests for arwiz.equivalence — Output equivalence checking."""

import numpy as np
import pytest
from arwiz.equivalence.core import DefaultEquivalenceChecker
from arwiz.equivalence.tolerance import arrays_close, deep_equal, is_close


@pytest.fixture
def checker() -> DefaultEquivalenceChecker:
    return DefaultEquivalenceChecker()


class TestIsClose:
    def test_exact_floats(self) -> None:
        assert is_close(1.0, 1.0)

    def test_within_tolerance(self) -> None:
        assert is_close(1.0, 1.0 + 1e-7)

    def test_beyond_tolerance(self) -> None:
        assert not is_close(1.0, 1.1, tolerance=1e-6)

    def test_both_nan_equal(self) -> None:
        assert is_close(float("nan"), float("nan"))

    def test_one_nan_not_equal(self) -> None:
        assert not is_close(float("nan"), 1.0)

    def test_inf_equal(self) -> None:
        assert is_close(float("inf"), float("inf"))

    def test_neg_inf_equal(self) -> None:
        assert is_close(float("-inf"), float("-inf"))

    def test_inf_vs_finite(self) -> None:
        assert not is_close(float("inf"), 1.0)

    def test_integers(self) -> None:
        assert is_close(42, 42)

    def test_strings(self) -> None:
        assert is_close("abc", "abc")
        assert not is_close("abc", "def")

    def test_relative_tolerance_large_values(self) -> None:
        # rel_tol * 1e12 = 1000 > 1.0, so passes despite atol=1e-6
        assert is_close(1e12, 1e12 + 1.0, tolerance=1e-6)

    def test_relative_tolerance_small_values(self) -> None:
        assert is_close(0.0, 0.5e-6, tolerance=1e-6)

    def test_both_zero(self) -> None:
        assert is_close(0.0, 0.0)


class TestArraysClose:
    def test_identical_arrays(self) -> None:
        a = np.array([1.0, 2.0, 3.0])
        assert arrays_close(a, a)[0]

    def test_close_arrays(self) -> None:
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([1.0 + 1e-9, 2.0, 3.0])
        assert arrays_close(a, b)[0]

    def test_nan_arrays_equal(self) -> None:
        a = np.array([1.0, float("nan"), 3.0])
        b = np.array([1.0, float("nan"), 3.0])
        assert arrays_close(a, b)[0]

    def test_different_nan_positions(self) -> None:
        a = np.array([float("nan"), 2.0])
        b = np.array([1.0, float("nan")])
        assert not arrays_close(a, b)[0]

    def test_shape_mismatch(self) -> None:
        a = np.array([1.0, 2.0])
        b = np.array([1.0, 2.0, 3.0])
        assert not arrays_close(a, b)[0]

    def test_not_arrays(self) -> None:
        assert not arrays_close([1, 2], [1, 2])[0]

    def test_all_nan_arrays(self) -> None:
        a = np.array([float("nan"), float("nan")])
        b = np.array([float("nan"), float("nan")])
        assert arrays_close(a, b)[0]


class TestDeepEqual:
    def test_primitives(self) -> None:
        assert deep_equal(1, 1)[0]
        assert deep_equal("hello", "hello")[0]
        assert deep_equal(True, True)[0]
        assert deep_equal(None, None)[0]

    def test_mismatched_types(self) -> None:
        assert not deep_equal(1, "1")[0]

    def test_none_vs_value(self) -> None:
        assert not deep_equal(None, 0)[0]

    def test_float_tolerance(self) -> None:
        assert deep_equal(1.0, 1.0 + 1e-7)[0]
        assert not deep_equal(1.0, 2.0)[0]

    def test_nan_equality(self) -> None:
        assert deep_equal(float("nan"), float("nan"))[0]

    def test_list_comparison(self) -> None:
        assert deep_equal([1, 2, 3], [1, 2, 3])[0]
        assert not deep_equal([1, 2], [1, 2, 3])[0]

    def test_nested_dict(self) -> None:
        a = {"x": 1.0, "y": {"z": [1, 2, 3]}}
        b = {"x": 1.0 + 1e-9, "y": {"z": [1, 2, 3]}}
        assert deep_equal(a, b)[0]

    def test_dict_key_mismatch(self) -> None:
        assert not deep_equal({"a": 1}, {"b": 1})[0]

    def test_tuple_comparison(self) -> None:
        assert deep_equal((1, 2), (1, 2))[0]

    def test_set_comparison(self) -> None:
        assert deep_equal({1, 2, 3}, {3, 2, 1})[0]

    def test_non_serializable_type(self) -> None:
        class CustomType:
            pass

        assert not deep_equal(CustomType(), 42)[0]

    def test_circular_reference(self) -> None:
        a: list = []
        a.append(a)
        result, reason = deep_equal(a, a, tolerance=0.0)
        assert result is True

    def test_circular_reference_dict(self) -> None:
        a: dict = {}
        a["self"] = a
        result, reason = deep_equal(a, a, tolerance=0.0)
        assert result is True

    def test_nested_lists_with_floats(self) -> None:
        a = [[1.0, 2.0], [3.0, 4.0]]
        b = [[1.0 + 1e-9, 2.0], [3.0, 4.0 + 1e-9]]
        assert deep_equal(a, b)[0]


class TestDefaultEquivalenceChecker:
    def test_check_equivalent(self, checker: DefaultEquivalenceChecker) -> None:
        ok, reason = checker.check_equivalence(42, 42)
        assert ok is True

    def test_check_not_equivalent(self, checker: DefaultEquivalenceChecker) -> None:
        ok, reason = checker.check_equivalence(42, 43)
        assert ok is False

    def test_compare_outputs(self, checker: DefaultEquivalenceChecker) -> None:
        result = checker.compare_outputs([1, 2], [1, 2])
        assert result["equivalent"] is True
        assert result["original_type"] == "list"
        assert result["optimized_type"] == "list"

    def test_compare_outputs_different(self, checker: DefaultEquivalenceChecker) -> None:
        result = checker.compare_outputs(1.0, 999.0)
        assert result["equivalent"] is False

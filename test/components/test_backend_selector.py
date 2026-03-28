from importlib import import_module

import pytest


def _import(name: str):
    return import_module(name)


def test_protocol_exists() -> None:
    mod = _import("arwiz.backend_selector.interface")
    assert hasattr(mod, "BackendSelectorProtocol")


def test_protocol_has_select_backends() -> None:
    from typing import Protocol, get_type_hints

    mod = _import("arwiz.backend_selector.interface")
    protocol = mod.BackendSelectorProtocol
    assert issubclass(protocol, Protocol)
    hints = get_type_hints(protocol.select_backends)
    assert "return" in hints


def test_protocol_has_get_manifest() -> None:
    from typing import get_type_hints

    mod = _import("arwiz.backend_selector.interface")
    protocol = mod.BackendSelectorProtocol
    hints = get_type_hints(protocol.get_manifest)
    assert "return" in hints


def test_protocol_has_is_backend_available() -> None:
    from typing import get_type_hints

    mod = _import("arwiz.backend_selector.interface")
    protocol = mod.BackendSelectorProtocol
    hints = get_type_hints(protocol.is_backend_available)
    assert "return" in hints


def test_protocol_has_rank_backends() -> None:
    from typing import get_type_hints

    mod = _import("arwiz.backend_selector.interface")
    protocol = mod.BackendSelectorProtocol
    hints = get_type_hints(protocol.rank_backends)
    assert "return" in hints


def test_protocol_has_exactly_4_methods() -> None:
    mod = _import("arwiz.backend_selector.interface")
    protocol = mod.BackendSelectorProtocol
    methods = [m for m in dir(protocol) if not m.startswith("_")]
    assert len(methods) == 4
    expected = {"select_backends", "get_manifest", "is_backend_available", "rank_backends"}
    assert set(methods) == expected


def test_core_has_default_implementation() -> None:
    mod = _import("arwiz.backend_selector.core")
    assert hasattr(mod, "DefaultBackendSelector")


def test_default_selector_methods_return_defaults() -> None:
    mod = _import("arwiz.backend_selector.core")
    selector = mod.DefaultBackendSelector()
    manifest = selector.get_manifest()

    assert isinstance(manifest, dict)
    assert len(manifest) == 8
    assert selector.select_backends("def f():\n    return 1\n", None) == []
    assert selector.rank_backends("def f():\n    return 1\n", None) == []


def test_select_backends_recommends_pyo3_for_string_operations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _import("arwiz.backend_selector.core")
    selector = mod.DefaultBackendSelector()
    monkeypatch.setattr(selector, "is_backend_available", lambda name: name == "pyo3")

    source = "def f(s):\n    return s.split(',')\n"
    assert selector.select_backends(source, None) == ["pyo3"]


def test_select_backends_returns_empty_for_vectorized_numpy_without_loops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _import("arwiz.backend_selector.core")
    selector = mod.DefaultBackendSelector()
    monkeypatch.setattr(selector, "is_backend_available", lambda name: True)

    source = "def f(a, b):\n    return np.dot(a, b) + np.sum(a)\n"
    assert selector.select_backends(source, None) == []


def test_select_backends_recommends_nested_loop_backends_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _import("arwiz.backend_selector.core")
    selector = mod.DefaultBackendSelector()
    monkeypatch.setattr(selector, "is_backend_available", lambda name: True)

    source = (
        "def f(n):\n"
        "    total = 0\n"
        "    for i in range(n):\n"
        "        for j in range(n):\n"
        "            total += i * j\n"
        "    return total\n"
    )
    assert selector.select_backends(source, None)[:2] == ["cython", "numba"]


def test_select_backends_filters_unavailable_backends(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _import("arwiz.backend_selector.core")
    selector = mod.DefaultBackendSelector()
    monkeypatch.setattr(selector, "is_backend_available", lambda name: name == "cython")

    source = (
        "def f(n):\n"
        "    total = 0\n"
        "    for i in range(n):\n"
        "        for j in range(n):\n"
        "            total += i * j\n"
        "    return total\n"
    )
    assert selector.select_backends(source, None) == ["cython"]


def test_rank_backends_returns_confidence_scores(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _import("arwiz.backend_selector.core")
    selector = mod.DefaultBackendSelector()
    monkeypatch.setattr(selector, "is_backend_available", lambda name: True)

    source = (
        "def f(arr, s):\n"
        "    out = np.zeros_like(arr)\n"
        "    for i in range(len(arr)):\n"
        "        out[i] = arr[i] * 2\n"
        "    return s.replace('a', 'b'), out\n"
    )
    ranked = selector.rank_backends(source, None)

    assert ranked
    assert all(isinstance(item, tuple) and len(item) == 2 for item in ranked)
    assert all(isinstance(name, str) for name, _ in ranked)
    assert all(isinstance(score, float) for _, score in ranked)
    assert all(0.0 <= score <= 1.0 for _, score in ranked)

    ranked_map = dict(ranked)
    assert ranked[0][0] == "pyo3"
    assert ranked_map["pyo3"] == 0.9


def test_init_reexports() -> None:
    mod = _import("arwiz.backend_selector")
    assert hasattr(mod, "BackendSelectorProtocol")
    assert hasattr(mod, "DefaultBackendSelector")
    assert hasattr(mod, "BackendManifest")
    assert mod.__all__ == ["BackendSelectorProtocol", "DefaultBackendSelector", "BackendManifest"]


def test_interface_imports_foundation_types() -> None:
    _import("arwiz.backend_selector.interface")


def test_select_backends_recommends_jax_cupy_for_array_ops_without_loops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _import("arwiz.backend_selector.core")
    selector = mod.DefaultBackendSelector()
    monkeypatch.setattr(selector, "is_backend_available", lambda name: True)

    source = "def f(a, b):\n    x = np.sum(a)\n    y = custom_transform(b)\n    return x + y\n"
    ranked = selector.rank_backends(source, None)
    ranked_names = [name for name, _ in ranked]

    assert "jax" in ranked_names
    assert "cupy" in ranked_names


def test_rank_backends_numexpr_confidence_in_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _import("arwiz.backend_selector.core")
    selector = mod.DefaultBackendSelector()
    monkeypatch.setattr(selector, "is_backend_available", lambda name: True)

    source = (
        "def f(data, n):\n"
        "    result = [0] * n\n"
        "    for i in range(n):\n"
        "        result[i] = data[i] * 2.0 / 3.0\n"
        "    return result\n"
    )
    ranked = selector.rank_backends(source, None)
    ranked_map = dict(ranked)

    assert "numexpr" in ranked_map
    assert 0.0 <= ranked_map["numexpr"] <= 1.0


def test_select_backends_jax_cupy_filtered_when_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _import("arwiz.backend_selector.core")
    selector = mod.DefaultBackendSelector()
    monkeypatch.setattr(selector, "is_backend_available", lambda name: name not in {"jax", "cupy"})

    source = "def f(a, b):\n    x = np.sum(a)\n    y = custom_transform(b)\n    return x + y\n"
    selected = selector.select_backends(source, None)

    assert "jax" not in selected
    assert "cupy" not in selected


def test_pyo3_confidence_is_0_9_for_string_operations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _import("arwiz.backend_selector.core")
    selector = mod.DefaultBackendSelector()
    monkeypatch.setattr(selector, "is_backend_available", lambda name: True)

    source = "def f(s):\n    return s.upper().strip()\n"
    ranked = selector.rank_backends(source, None)
    ranked_map = dict(ranked)

    assert "pyo3" in ranked_map
    assert ranked_map["pyo3"] == 0.9
    assert ranked[0][0] == "pyo3"


def test_taichi_never_selected_by_selector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _import("arwiz.backend_selector.core")
    selector = mod.DefaultBackendSelector()
    monkeypatch.setattr(selector, "is_backend_available", lambda name: True)

    sources = [
        "def f(s):\n    return s.split(',')\n",
        "def f(n):\n    for i in range(n):\n        pass\n",
        "def f(arr):\n    return np.sum(arr)\n",
    ]
    for source in sources:
        selected = selector.select_backends(source, None)
        assert "taichi" not in selected


def test_taichi_always_reports_unavailable() -> None:
    mod = _import("arwiz.backend_selector.core")
    selector = mod.DefaultBackendSelector()

    assert selector.is_backend_available("taichi") is False


def test_pure_numpy_vectorized_with_safe_builtins_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _import("arwiz.backend_selector.core")
    selector = mod.DefaultBackendSelector()
    monkeypatch.setattr(selector, "is_backend_available", lambda name: True)

    source = (
        "def f(a, b):\n"
        "    x = np.array(a)\n"
        "    y = np.zeros(len(b))\n"
        "    s = int(np.sum(x))\n"
        "    print(s)\n"
        "    return s\n"
    )
    assert selector.select_backends(source, None) == []


def test_loops_with_array_ops_no_strings_returns_backends(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _import("arwiz.backend_selector.core")
    selector = mod.DefaultBackendSelector()
    monkeypatch.setattr(selector, "is_backend_available", lambda name: True)

    source = (
        "def f(data, n):\n"
        "    result = np.zeros(n)\n"
        "    for i in range(n):\n"
        "        result[i] = np.sqrt(data[i])\n"
        "    return result\n"
    )
    ranked = selector.rank_backends(source, None)
    ranked_names = [name for name, _ in ranked]
    assert len(ranked_names) > 0
    assert "numba" in ranked_names


def test_parallel_safe_loops_recommends_numba_parallel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _import("arwiz.backend_selector.core")
    selector = mod.DefaultBackendSelector()
    monkeypatch.setattr(selector, "is_backend_available", lambda name: True)

    source = (
        "def f(data, n):\n"
        "    result = np.zeros(n)\n"
        "    for i in range(n):\n"
        "        result[i] = data[i] * 2.0\n"
        "    return result\n"
    )
    ranked = selector.rank_backends(source, None)
    ranked_map = dict(ranked)
    assert "numba_parallel" in ranked_map
    assert ranked_map["numba_parallel"] == 0.75

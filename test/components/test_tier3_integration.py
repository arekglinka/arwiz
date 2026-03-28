from importlib import import_module

import pytest


def _import(name: str):
    return import_module(name)


def test_backend_template_map_covers_all_tier3_backends() -> None:
    mod = _import("arwiz.orchestrator.core")
    mapping = mod.DefaultOrchestrator._BACKEND_TEMPLATE_MAP

    for tier3_backend in ("pyo3", "cffi"):
        assert tier3_backend in mapping, f"Tier 3 backend '{tier3_backend}' missing from map"
        assert isinstance(mapping[tier3_backend], str)
        assert mapping[tier3_backend] != ""


def test_taichi_not_in_backend_template_map() -> None:
    mod = _import("arwiz.orchestrator.core")
    mapping = mod.DefaultOrchestrator._BACKEND_TEMPLATE_MAP

    assert "taichi" not in mapping


def test_tier3_template_names_match_registered_templates() -> None:
    mod = _import("arwiz.orchestrator.core")
    mapping = mod.DefaultOrchestrator._BACKEND_TEMPLATE_MAP
    optimizer_mod = _import("arwiz.template_optimizer.core")
    optimizer = optimizer_mod.DefaultTemplateOptimizer()
    registered = set(optimizer.list_templates())

    for tier3_backend in ("pyo3", "cffi"):
        template_name = mapping[tier3_backend]
        assert template_name in registered, (
            f"Template '{template_name}' for backend '{tier3_backend}' not registered"
        )


def test_selector_to_orchestrator_pyo3_pipeline_mock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selector_mod = _import("arwiz.backend_selector.core")
    selector = selector_mod.DefaultBackendSelector()
    monkeypatch.setattr(selector, "is_backend_available", lambda name: name == "pyo3")

    source = "def f(s):\n    return s.split(',')\n"
    selected = selector.select_backends(source, None)
    assert "pyo3" in selected

    orchestrator_mod = _import("arwiz.orchestrator.core")
    mapping = orchestrator_mod.DefaultOrchestrator._BACKEND_TEMPLATE_MAP
    assert mapping["pyo3"] == "pyo3_optimize"


def test_cffi_reachable_via_selector_heuristic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selector_mod = _import("arwiz.backend_selector.core")
    selector = selector_mod.DefaultBackendSelector()
    monkeypatch.setattr(selector, "is_backend_available", lambda name: True)

    loop_arithmetic = (
        "def f(data, n):\n"
        "    result = [0] * n\n"
        "    for i in range(n):\n"
        "        result[i] = data[i] * 2\n"
        "    return result\n"
    )
    ranked = selector.rank_backends(loop_arithmetic, None)
    ranked_map = dict(ranked)

    assert "cffi" in ranked_map
    assert ranked_map["cffi"] == 0.4
    assert ranked_map["numexpr"] > ranked_map["cffi"]

    string_source = "def f(s):\n    return s.split(',')\n"
    selected = selector.select_backends(string_source, None)
    assert "cffi" not in selected

    orchestrator_mod = _import("arwiz.orchestrator.core")
    mapping = orchestrator_mod.DefaultOrchestrator._BACKEND_TEMPLATE_MAP
    assert mapping["cffi"] == "cffi_optimize"


def test_taichi_always_unavailable_through_selector() -> None:
    manifest_mod = _import("arwiz.backend_selector.manifest")
    manifest = manifest_mod.BackendManifest()

    available, reason = manifest.check_availability("taichi")
    assert available is False
    assert "Python <=3.10" in reason

    selector_mod = _import("arwiz.backend_selector.core")
    selector = selector_mod.DefaultBackendSelector()
    assert selector.is_backend_available("taichi") is False


def test_tier3_cffi_template_produces_valid_python() -> None:
    optimizer_mod = _import("arwiz.template_optimizer.core")
    optimizer = optimizer_mod.DefaultTemplateOptimizer()

    source = (
        "def f(data, n):\n"
        "    result = [0] * n\n"
        "    for i in range(n):\n"
        "        result[i] = data[i] * 2\n"
        "    return result\n"
    )
    transformed = optimizer.apply_template(source, "cffi_optimize")
    compile(transformed, "<string>", "exec")


def test_tier3_pyo3_template_produces_non_empty_output() -> None:
    optimizer_mod = _import("arwiz.template_optimizer.core")
    optimizer = optimizer_mod.DefaultTemplateOptimizer()

    source = "def f(s):\n    return s.upper().strip()\n"
    transformed = optimizer.apply_template(source, "pyo3_optimize")
    assert len(transformed) > len(source)
    assert "pyo3" in transformed.lower() or "rust" in transformed.lower()


def test_tier3_fallback_chain_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    selector_mod = _import("arwiz.backend_selector.core")
    selector = selector_mod.DefaultBackendSelector()
    available_backends = {"numba", "pyo3", "cffi"}
    monkeypatch.setattr(selector, "is_backend_available", lambda name: name in available_backends)

    source = "def f(s):\n    return s.upper().strip()\n"
    selected = selector.select_backends(source, None)

    assert "pyo3" in selected

    orchestrator_mod = _import("arwiz.orchestrator.core")
    mapping = orchestrator_mod.DefaultOrchestrator._BACKEND_TEMPLATE_MAP
    for backend in selected:
        template = mapping.get(backend)
        if template:
            optimizer_mod = _import("arwiz.template_optimizer.core")
            optimizer = optimizer_mod.DefaultTemplateOptimizer()
            assert template in optimizer.list_templates()


def test_tier3_backend_falls_back_to_lower_tier(monkeypatch: pytest.MonkeyPatch) -> None:
    selector_mod = _import("arwiz.backend_selector.core")
    selector = selector_mod.DefaultBackendSelector()
    monkeypatch.setattr(selector, "is_backend_available", lambda name: name == "numba")

    source = (
        "def f(arr, s):\n"
        "    out = np.zeros_like(arr)\n"
        "    for i in range(len(arr)):\n"
        "        out[i] = arr[i] * 2\n"
        "    return s.replace('a', 'b'), out\n"
    )
    selected = selector.select_backends(source, None)

    assert "pyo3" not in selected
    assert "numba" in selected

    orchestrator_mod = _import("arwiz.orchestrator.core")
    mapping = orchestrator_mod.DefaultOrchestrator._BACKEND_TEMPLATE_MAP
    assert mapping["numba"] == "numba_jit"

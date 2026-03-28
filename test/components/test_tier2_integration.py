from importlib import import_module

import pytest


def _import(name: str):
    return import_module(name)


def test_backend_template_map_covers_all_tier2_backends() -> None:
    mod = _import("arwiz.orchestrator.core")
    mapping = mod.DefaultOrchestrator._BACKEND_TEMPLATE_MAP

    for tier2_backend in ("jax", "cupy", "numexpr"):
        assert tier2_backend in mapping, f"Tier 2 backend '{tier2_backend}' missing from map"
        assert isinstance(mapping[tier2_backend], str)
        assert mapping[tier2_backend] != ""


def test_tier2_template_names_match_registered_templates() -> None:
    mod = _import("arwiz.orchestrator.core")
    mapping = mod.DefaultOrchestrator._BACKEND_TEMPLATE_MAP
    optimizer_mod = _import("arwiz.template_optimizer.core")
    optimizer = optimizer_mod.DefaultTemplateOptimizer()
    registered = set(optimizer.list_templates())

    for tier2_backend in ("jax", "cupy", "numexpr"):
        template_name = mapping[tier2_backend]
        assert template_name in registered, (
            f"Template '{template_name}' for backend '{tier2_backend}' not registered"
        )


def test_selector_to_orchestrator_jax_pipeline_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    selector_mod = _import("arwiz.backend_selector.core")
    selector = selector_mod.DefaultBackendSelector()
    monkeypatch.setattr(selector, "is_backend_available", lambda name: name == "jax")

    source = "def f(a, b):\n    x = np.sum(a)\n    y = custom_op(b)\n    return x + y\n"
    selected = selector.select_backends(source, None)
    assert "jax" in selected

    orchestrator_mod = _import("arwiz.orchestrator.core")
    mapping = orchestrator_mod.DefaultOrchestrator._BACKEND_TEMPLATE_MAP
    assert mapping["jax"] == "jax_optimize"


def test_selector_to_orchestrator_cupy_pipeline_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    selector_mod = _import("arwiz.backend_selector.core")
    selector = selector_mod.DefaultBackendSelector()
    monkeypatch.setattr(selector, "is_backend_available", lambda name: name == "cupy")

    source = "def f(a, b):\n    x = np.sum(a)\n    y = custom_op(b)\n    return x + y\n"
    selected = selector.select_backends(source, None)
    assert "cupy" in selected

    orchestrator_mod = _import("arwiz.orchestrator.core")
    mapping = orchestrator_mod.DefaultOrchestrator._BACKEND_TEMPLATE_MAP
    assert mapping["cupy"] == "cupy_optimize"


def test_selector_to_orchestrator_numexpr_pipeline_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    selector_mod = _import("arwiz.backend_selector.core")
    selector = selector_mod.DefaultBackendSelector()
    monkeypatch.setattr(selector, "is_backend_available", lambda name: name == "numexpr")

    source = (
        "def f(data, n):\n"
        "    result = [0] * n\n"
        "    for i in range(n):\n"
        "        result[i] = data[i] * 2 + data[i] ** 2\n"
        "    return result\n"
    )
    selected = selector.select_backends(source, None)
    assert "numexpr" in selected

    orchestrator_mod = _import("arwiz.orchestrator.core")
    mapping = orchestrator_mod.DefaultOrchestrator._BACKEND_TEMPLATE_MAP
    assert mapping["numexpr"] == "numexpr_optimize"


def test_tier2_templates_produce_valid_python() -> None:
    optimizer_mod = _import("arwiz.template_optimizer.core")
    optimizer = optimizer_mod.DefaultTemplateOptimizer()

    sources = {
        "jax_optimize": ("def f(arr):\n    return np.sum(arr)\n"),
        "cupy_optimize": ("def f(arr):\n    values = np.array(arr)\n    return np.sum(values)\n"),
        "numexpr_optimize": (
            "def f(a, b):\n"
            "    result = a.copy()\n"
            "    for i in range(len(a)):\n"
            "        result[i] = a[i] ** 2 + b[i] ** 2\n"
            "    return result\n"
        ),
    }

    for template_name, source in sources.items():
        transformed = optimizer.apply_template(source, template_name)
        compile(transformed, "<string>", "exec")

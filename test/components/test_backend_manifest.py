from importlib import import_module


def _import(name: str):
    return import_module(name)


def test_manifest_module_exports_backend_manifest() -> None:
    mod = _import("arwiz.backend_selector.manifest")
    assert hasattr(mod, "BackendManifest")


def test_default_manifest_contains_all_backends() -> None:
    mod = _import("arwiz.backend_selector.manifest")
    manifest = mod.BackendManifest()
    all_backends = manifest.all_backends()

    expected = {"numba", "cython", "jax", "cupy", "numexpr", "pyo3", "cffi", "taichi"}
    assert set(all_backends) == expected


def test_numba_entry_matches_expected_metadata() -> None:
    mod = _import("arwiz.backend_selector.manifest")
    manifest = mod.BackendManifest()
    numba = manifest.get_backend("numba")

    assert numba.tier == 1
    assert numba.performance_range == (10.0, 200.0)
    assert numba.install_hint == "pip install numba"
    assert numba.ast_patterns == ["for_loop", "numeric_ops", "numpy_calls", "nested_loops"]


def test_taichi_is_always_unavailable_with_reason() -> None:
    mod = _import("arwiz.backend_selector.manifest")
    manifest = mod.BackendManifest()

    available, reason = manifest.check_availability("taichi")
    assert available is False
    assert reason == "Taichi requires Python <=3.10, project uses Python 3.12+"

    taichi = manifest.get_backend("taichi")
    assert taichi.is_available is False
    assert taichi.availability_reason == "Taichi requires Python <=3.10, project uses Python 3.12+"


def test_unknown_backend_returns_false_with_reason() -> None:
    mod = _import("arwiz.backend_selector.manifest")
    manifest = mod.BackendManifest()

    available, reason = manifest.check_availability("definitely_missing_backend")
    assert available is False
    assert reason == "Backend 'definitely_missing_backend' is not registered"


def test_caches_importlib_lookup(monkeypatch) -> None:
    mod = _import("arwiz.backend_selector.manifest")
    manifest = mod.BackendManifest()

    calls = {"count": 0}

    def fake_find_spec(_name: str):
        calls["count"] += 1

        class Spec:
            pass

        return Spec()

    monkeypatch.setattr(mod.importlib.util, "find_spec", fake_find_spec)

    first = manifest.check_availability("jax")
    second = manifest.check_availability("jax")

    assert first == second
    assert calls["count"] == 1


def test_all_backends_populates_availability_fields() -> None:
    mod = _import("arwiz.backend_selector.manifest")
    manifest = mod.BackendManifest()

    all_backends = manifest.all_backends()

    assert all_backends["numba"].is_available is True
    assert all_backends["taichi"].is_available is False
    assert (
        all_backends["taichi"].availability_reason
        == "Taichi requires Python <=3.10, project uses Python 3.12+"
    )


def test_jax_entry_matches_expected_metadata() -> None:
    mod = _import("arwiz.backend_selector.manifest")
    manifest = mod.BackendManifest()
    jax = manifest.get_backend("jax")

    assert jax.tier == 2
    assert jax.performance_range == (5.0, 100.0)
    assert jax.install_hint == "pip install jax jaxlib"
    assert "numpy_calls" in jax.ast_patterns
    assert "vectorizable_ops" in jax.ast_patterns
    assert any("GPU" in s or "XLA" in s for s in jax.strengths)


def test_cupy_entry_matches_expected_metadata() -> None:
    mod = _import("arwiz.backend_selector.manifest")
    manifest = mod.BackendManifest()
    cupy = manifest.get_backend("cupy")

    assert cupy.tier == 2
    assert cupy.performance_range == (10.0, 100.0)
    assert cupy.install_hint == "pip install cupy-cuda12x"
    assert "numpy_calls" in cupy.ast_patterns
    assert any("GPU" in s or "CUDA" in s for s in cupy.strengths)


def test_numexpr_entry_matches_expected_metadata() -> None:
    mod = _import("arwiz.backend_selector.manifest")
    manifest = mod.BackendManifest()
    numexpr = manifest.get_backend("numexpr")

    assert numexpr.tier == 2
    assert numexpr.performance_range == (2.0, 15.0)
    assert numexpr.install_hint == "pip install numexpr"
    assert "arithmetic_expressions" in numexpr.ast_patterns
    assert "no compilation needed" in numexpr.strengths


def test_tier2_availability_checks_return_reason_when_not_installed() -> None:
    mod = _import("arwiz.backend_selector.manifest")
    manifest = mod.BackendManifest()

    for name in ("jax", "cupy", "numexpr"):
        available, reason = manifest.check_availability(name)
        if not available:
            assert reason is not None
            assert "not installed" in reason


def test_pyo3_entry_matches_expected_metadata() -> None:
    mod = _import("arwiz.backend_selector.manifest")
    manifest = mod.BackendManifest()
    pyo3 = manifest.get_backend("pyo3")

    assert pyo3.tier == 3
    assert pyo3.performance_range == (10.0, 200.0)
    assert pyo3.install_hint == "pip install maturin"
    assert "string_operations" in pyo3.ast_patterns
    assert "nested_loops" in pyo3.ast_patterns
    assert "complex_logic" in pyo3.ast_patterns
    assert "memory_operations" in pyo3.ast_patterns
    assert any("string" in s.lower() for s in pyo3.strengths)
    assert any("rust" in s.lower() or "toolchain" in s.lower() for s in pyo3.limitations)


def test_cffi_entry_matches_expected_metadata() -> None:
    mod = _import("arwiz.backend_selector.manifest")
    manifest = mod.BackendManifest()
    cffi = manifest.get_backend("cffi")

    assert cffi.tier == 3
    assert cffi.performance_range == (5.0, 50.0)
    assert cffi.install_hint == "pip install cffi"
    assert "c_api_calls" in cffi.ast_patterns
    assert "memory_operations" in cffi.ast_patterns
    assert any("C" in s for s in cffi.strengths)
    assert any("platform" in s.lower() for s in cffi.limitations)


def test_taichi_entry_matches_expected_metadata() -> None:
    mod = _import("arwiz.backend_selector.manifest")
    manifest = mod.BackendManifest()
    taichi = manifest.get_backend("taichi")

    assert taichi.tier == 3
    assert taichi.performance_range == (10.0, 500.0)
    assert taichi.is_available is False
    assert "Python <=3.10" in taichi.availability_reason
    assert taichi.ast_patterns == []
    assert any("physical" in s.lower() or "spatial" in s.lower() for s in taichi.best_for)


def test_tier3_availability_checks_return_reason_when_not_installed() -> None:
    mod = _import("arwiz.backend_selector.manifest")
    manifest = mod.BackendManifest()

    available, reason = manifest.check_availability("taichi")
    assert available is False
    assert reason is not None

    for name in ("pyo3", "cffi"):
        available, reason = manifest.check_availability(name)
        if not available:
            assert reason is not None
            assert "not installed" in reason


def test_all_tier3_backends_have_positive_performance_range() -> None:
    mod = _import("arwiz.backend_selector.manifest")
    manifest = mod.BackendManifest()

    for name in ("pyo3", "cffi", "taichi"):
        backend = manifest.get_backend(name)
        low, high = backend.performance_range
        assert low > 0, f"{name} lower bound must be positive"
        assert high >= low, f"{name} upper bound must >= lower bound"

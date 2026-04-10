from typing import Any, Protocol


class _HotSpotLike(Protocol):
    function_name: str
    file_path: str
    line_range: tuple[int, int]
    cumulative_time_ms: int
    self_time_ms: int


def _base_context(source: str, hotspot: _HotSpotLike) -> str:
    return (
        f"Target function: {hotspot.function_name}\n"
        f"File: {hotspot.file_path}\n"
        f"Lines: {hotspot.line_range[0]}-{hotspot.line_range[1]}\n"
        f"Cumulative time (ms): {hotspot.cumulative_time_ms}\n"
        f"Self time (ms): {hotspot.self_time_ms}\n"
        "Return ONLY Python code in a single ```python fenced block.\n"
        "Preserve behavior and function signature.\n"
        "\n"
        "Source:\n"
        f"{source}\n"
    )


def build_vectorization_prompt(source: str, hotspot: _HotSpotLike) -> str:
    return (
        "Optimize this Python function by vectorizing loops with NumPy.\n"
        "Prefer numpy array operations, np.where, reductions "
        "like np.sum, and avoid Python loops when possible.\n" + _base_context(source, hotspot)
    )


def build_numba_jit_prompt(source: str, hotspot: _HotSpotLike) -> str:
    return (
        "Optimize this Python function for JIT compilation with Numba.\n"
        "Add @njit and adjust code for numba compatibility "
        "(avoid Python objects and unsupported constructs).\n" + _base_context(source, hotspot)
    )


def build_cython_prompt(source: str, hotspot: _HotSpotLike) -> str:
    return (
        "Optimize this Python function using Cython typed memoryviews.\n"
        "Use typed memoryviews (e.g. double[:]), prefer cython.int/cython.double where helpful, "
        "and include compiler directives like boundscheck=False and wraparound=False.\n"
        + _base_context(source, hotspot)
    )


def build_numba_parallel_prompt(source: str, hotspot: _HotSpotLike) -> str:
    return (
        "Optimize this Python function for parallel execution with Numba.\n"
        "Use @numba.njit(parallel=True), convert independent range loops "
        "to numba.prange, and preserve data independence across iterations.\n"
        + _base_context(source, hotspot)
    )


def build_caching_prompt(source: str, hotspot: _HotSpotLike) -> str:
    return (
        "Optimize this Python function by adding memoization/caching where safe.\n"
        "Prefer functools.lru_cache(maxsize=None) for pure deterministic functions.\n"
        + _base_context(source, hotspot)
    )


def build_batch_io_prompt(source: str, hotspot: _HotSpotLike) -> str:
    return (
        "Optimize this Python function by batching I/O operations.\n"
        "Accumulate writes or reads and perform fewer larger "
        "operations when behavior remains equivalent.\n" + _base_context(source, hotspot)
    )


def build_cupy_prompt(source: str, hotspot: _HotSpotLike) -> str:
    return (
        "Optimize this Python function for GPU acceleration using CuPy.\n"
        "Replace NumPy operations with CuPy equivalents, convert inputs using cp.asarray, "
        "and convert outputs back with cp.asnumpy.\n" + _base_context(source, hotspot)
    )


def build_numexpr_prompt(source: str, hotspot: _HotSpotLike) -> str:
    return (
        "Optimize this Python function using NumExpr for element-wise arithmetic.\n"
        'Prefer replacing simple array element loops with numexpr.evaluate("...") '
        "for arithmetic expressions and preserve semantics.\n" + _base_context(source, hotspot)
    )


def build_jax_prompt(source: str, hotspot: _HotSpotLike) -> str:
    return (
        "Optimize this Python function using JAX for array operations.\n"
        "Use jax.numpy (jnp) in place of NumPy where appropriate and add @jax.jit "
        "to compile numerical hot paths while preserving behavior.\n"
        + _base_context(source, hotspot)
    )


def build_cffi_prompt(source: str, hotspot: _HotSpotLike) -> str:
    return (
        "Optimize this Python function using CFFI and generated C code.\n"
        "Define the C signature in ffi.cdef(...), compile C source with ffi.verify(...), "
        "and provide a thin Python wrapper that marshals arguments safely.\n"
        + _base_context(source, hotspot)
    )


def build_pyo3_prompt(source: str, hotspot: _HotSpotLike) -> str:
    return (
        "Optimize this Python function using Rust + PyO3 bindings.\n"
        "Prioritize string-heavy transformations, expose Rust functions with #[pyfunction], "
        "and include build guidance using maturin develop.\n" + _base_context(source, hotspot)
    )


def build_taichi_prompt(source: str, hotspot: _HotSpotLike) -> str:
    return (
        "Taichi GPU acceleration is unavailable on this system.\n"
        "Taichi requires Python <=3.10, but this project uses Python 3.12+.\n"
        "Consider using CuPy or JAX for GPU acceleration instead.\n"
        + _base_context(source, hotspot)
    )


def build_manifest_context(manifest: dict[str, Any], available_only: bool = True) -> str:
    def _to_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            return [str(item) for item in value if str(item).strip()]
        text = str(value).strip()
        return [text] if text else []

    def _format_perf(value: Any) -> str:
        if isinstance(value, tuple) and len(value) == 2:
            return f"{value[0]}x-{value[1]}x"
        if isinstance(value, list) and len(value) == 2:
            return f"{value[0]}x-{value[1]}x"
        return str(value) if value else "unknown"

    grouped: dict[int, list[list[str]]] = {}

    for backend_key, backend in manifest.items():
        is_available = bool(getattr(backend, "is_available", True))
        if available_only and not is_available:
            continue

        tier_raw = getattr(backend, "tier", 0)
        tier = tier_raw if isinstance(tier_raw, int) else 0
        name = str(getattr(backend, "name", backend_key))
        strengths = _to_list(getattr(backend, "strengths", []))
        limitations = _to_list(getattr(backend, "limitations", []))
        best_for = _to_list(getattr(backend, "best_for", []))
        performance = _format_perf(getattr(backend, "performance_range", None))
        install_hint = str(getattr(backend, "install_hint", ""))
        availability_reason = str(getattr(backend, "availability_reason", "") or "")

        lines = [
            f"Backend: {name}",
            f"- Tier: {tier}",
            "- Strengths:",
            *[f"  - {entry}" for entry in strengths],
            "- Limitations:",
            *[f"  - {entry}" for entry in limitations],
            "- Best for:",
            *[f"  - {entry}" for entry in best_for],
            f"- Performance range: {performance}",
        ]

        if not is_available:
            if availability_reason:
                lines.append(f"- Availability: unavailable ({availability_reason})")
            else:
                lines.append("- Availability: unavailable")
        else:
            lines.append("- Availability: available")

        if install_hint.strip():
            lines.append(f"- Install hint: {install_hint}")

        grouped.setdefault(tier, []).append(lines)

    if not grouped:
        return "Backend manifest context: no backends available under current filters."

    output: list[str] = ["Backend manifest context:"]
    for tier in sorted(grouped):
        output.append(f"Tier {tier} backends:")
        for backend_lines in sorted(grouped[tier], key=lambda entry: entry[0]):
            output.extend(backend_lines)
            output.append("")

    return "\n".join(output).strip()

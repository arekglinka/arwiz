from arwiz.foundation import HotSpot


def _base_context(source: str, hotspot: HotSpot) -> str:
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


def build_vectorization_prompt(source: str, hotspot: HotSpot) -> str:
    return (
        "Optimize this Python function by vectorizing loops with NumPy.\n"
        "Prefer numpy array operations, np.where, reductions "
        "like np.sum, and avoid Python loops when possible.\n" + _base_context(source, hotspot)
    )


def build_numba_jit_prompt(source: str, hotspot: HotSpot) -> str:
    return (
        "Optimize this Python function for JIT compilation with Numba.\n"
        "Add @njit and adjust code for numba compatibility "
        "(avoid Python objects and unsupported constructs).\n" + _base_context(source, hotspot)
    )


def build_caching_prompt(source: str, hotspot: HotSpot) -> str:
    return (
        "Optimize this Python function by adding memoization/caching where safe.\n"
        "Prefer functools.lru_cache(maxsize=None) for pure deterministic functions.\n"
        + _base_context(source, hotspot)
    )


def build_batch_io_prompt(source: str, hotspot: HotSpot) -> str:
    return (
        "Optimize this Python function by batching I/O operations.\n"
        "Accumulate writes or reads and perform fewer larger "
        "operations when behavior remains equivalent.\n" + _base_context(source, hotspot)
    )

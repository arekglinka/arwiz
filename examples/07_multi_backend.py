#!/usr/bin/env python3
"""Multi-backend optimization demonstration.

Shows arwiz's backend selector, template optimizer, and LLM prompt
enhancement across multiple function patterns.

Run: uv run python examples/07_multi_backend.py
"""

from importlib import import_module

import numpy as np
from arwiz.backend_selector import BackendManifest, DefaultBackendSelector
from arwiz.llm_optimizer.prompts import build_manifest_context
from arwiz.template_optimizer import DefaultTemplateOptimizer

SEP = "=" * 64


def numeric_loop(n: int = 1000) -> float:
    total = 0.0
    for i in range(n):
        total += (i * i + 1.0) / (i + 1.0)
    return total


def string_processing(texts: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for text in texts:
        words = text.strip().lower().split()
        for word in words:
            cleaned = word.strip(".,!?;:'\"()[]{}")
            if cleaned:
                counts[cleaned] = counts.get(cleaned, 0) + 1
    return counts


def numpy_array_ops(data: np.ndarray) -> np.ndarray:
    normalized = (data - np.mean(data)) / (np.std(data) + 1e-10)
    result = np.sqrt(np.abs(normalized)) * np.sign(normalized)
    return result


def elementwise_arithmetic(arr: list[float]) -> list[float]:
    n = len(arr)
    result = [0.0] * n
    for i in range(n):
        result[i] = 3.0 * arr[i] * arr[i] - 2.0 * arr[i] + 1.0
    return result


def main() -> None:
    selector = DefaultBackendSelector()
    optimizer = DefaultTemplateOptimizer()
    manifest = BackendManifest()

    print(SEP)
    print("BACKEND OVERVIEW")
    print(SEP)
    all_backends = manifest.all_backends()
    available = [name for name, info in all_backends.items() if info.is_available]
    unavailable = [name for name, info in all_backends.items() if not info.is_available]
    print(f"Total backends: {len(all_backends)}")
    print(f"Available:      {available}")
    print(f"Unavailable:    {unavailable}")
    print()

    print(SEP)
    print("BACKEND MANIFEST CONTEXT (for LLM consultation)")
    print(SEP)
    ctx = build_manifest_context(all_backends, available_only=True)
    print(ctx)
    print()

    sample_functions = [
        ("numeric_loop", numeric_loop),
        ("string_processing", string_processing),
        ("numpy_array_ops", numpy_array_ops),
        ("elementwise_arithmetic", elementwise_arithmetic),
    ]

    rows: list[dict[str, str]] = []

    for func_name, func in sample_functions:
        source = import_module("inspect").getsource(func)
        print(SEP)
        print(f"FUNCTION: {func_name}")
        print(SEP)
        print(f"Source length: {len(source)} chars")
        print()

        selected = selector.select_backends(source)
        ranked = selector.rank_backends(source)
        print(f"Selected backends:  {selected or '(none — all recommended backends unavailable)'}")
        print("Ranked (with confidence):")
        if ranked:
            for name, conf in ranked:
                available_marker = "*" if selector.is_backend_available(name) else " "
                print(f"  {available_marker} {name:<12} confidence={conf:.2f}")
            print("  (* = available on this system)")
        else:
            print("  (no backends recommended — pattern may be already optimized)")
        print()

        detected = optimizer.detect_applicable_templates(source)
        print(f"Detected templates: {detected}")
        print()

        top_backend = ranked[0][0] if ranked else "none"
        top_conf = f"{ranked[0][1]:.2f}" if ranked else "n/a"
        templates_str = ", ".join(detected) if detected else "none"
        rows.append(
            {
                "function": func_name,
                "backend": top_backend,
                "confidence": top_conf,
                "templates": templates_str,
                "selected": ", ".join(selected) if selected else "none",
            }
        )

    print(SEP)
    print("SUMMARY TABLE")
    print(SEP)
    header = f"{'Function':<24} | {'Backend':<12} | {'Conf':>5} | {'Selected':<20} | Templates"
    print(header)
    print("-" * len(header))
    for row in rows:
        print(
            f"{row['function']:<24} | {row['backend']:<12} | "
            f"{row['confidence']:>5} | {row['selected']:<20} | {row['templates']}"
        )

    print()
    print(SEP)
    print("KEY OBSERVATIONS")
    print(SEP)
    print(f"- Available backends on this system: {available}")
    print("- Backend selector ranks by heuristic confidence (0.0–1.0).")
    print("  Unavailable backends are filtered from selection output.")
    print("- Template optimizer detects applicable transformations independently")
    print("  of backend availability (some templates produce Python, some Rust/C).")
    print("- numeric_loop: simple loop with arithmetic, no array indexing")
    print("  → no backend recommended (heuristic needs array/str patterns)")
    print("  → templates detected: vectorize_loop, numba_jit")
    print("- string_processing: nested loops + string ops")
    print("  → pyo3 (0.9) recommended but unavailable, cython/numba (0.7) also hit")
    print("  → only numba survives availability filter")
    print("- numpy_array_ops: pure NumPy vectorized calls, no loops")
    print("  → short-circuited as already optimal (no backends, no templates)")
    print("- elementwise_arithmetic: loop with arithmetic on list subscripts")
    print("  → no backend recommended (heuristic needs sequential memory patterns)")
    print(
        "  → templates detected: vectorize_loop, numba_jit, numba_parallel, cython, numexpr, cffi"
    )
    print("- build_manifest_context() formats the manifest for LLM prompt injection.")


if __name__ == "__main__":
    main()

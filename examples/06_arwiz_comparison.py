# Comparison: arwiz template optimizer vs hand-written numba
#
# Demonstrates arwiz's DefaultTemplateOptimizer and DefaultEquivalenceChecker
# by running the 05_baseline's compute_risk_scores through template detection,
# template application, equivalence checking, and benchmarking against a
# hand-written numba variant.
#
# Run it:
#   uv run python examples/06_arwiz_comparison.py

import importlib.util
import inspect
import time

import numba
import numpy as np
from arwiz.equivalence import DefaultEquivalenceChecker
from arwiz.template_optimizer import DefaultTemplateOptimizer

# --- Load baseline module via importlib to avoid path issues ---
spec = importlib.util.spec_from_file_location("baseline", "examples/05_pandas_baseline.py")
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)

generate_data = baseline.generate_data
compute_risk_scores = baseline.compute_risk_scores
source_code = inspect.getsource(compute_risk_scores)


@numba.njit
def compute_risk_scores_numba(
    closes: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    volumes: np.ndarray,
    window: int = 20,
) -> np.ndarray:
    """Hand-optimized numba version of compute_risk_scores.

    Key changes from original:
    - Uses @numba.njit decorator
    - Returns np.ndarray instead of list
    - Manual clamp instead of np.clip (scalar np.clip fails in nopython mode)
    """
    n = len(closes)
    scores = np.empty(n, dtype=np.float64)
    for i in range(n):
        start = max(0, i - window)
        if i - start < 2:
            scores[i] = 50.0
            continue
        slice_close = closes[start:i]
        slice_high = highs[start:i]
        slice_low = lows[start:i]
        slice_vol = volumes[start:i]
        mean_c = np.mean(slice_close)
        std_c = np.std(slice_close)
        if std_c < 1e-10:
            scores[i] = 50.0
            continue
        z = (closes[i] - mean_c) / std_c
        avg_range = np.mean(slice_high - slice_low)
        mean_vol = np.mean(slice_vol)
        vol_ratio = slice_vol[-1] / max(mean_vol, 1e-10)
        score = 50.0 + 20.0 * z + 10.0 * (avg_range / max(mean_c, 1e-10)) * 100
        if vol_ratio > 2.0:
            score -= 15.0
        elif vol_ratio < 0.5:
            score += 10.0
        if score < 0.0:
            score = 0.0
        elif score > 100.0:
            score = 100.0
        scores[i] = score
    return scores


SEP = "=" * 64
ITERATIONS = 5
N_ROWS = 500


def benchmark(func, *args, warmup: int = 0) -> float:
    """Run func ITERATIONS times (+ warmup), return mean time in ms."""
    for _ in range(warmup):
        func(*args)
    times = []
    for _ in range(ITERATIONS):
        t0 = time.perf_counter()
        func(*args)
        times.append((time.perf_counter() - t0) * 1000)
    return sum(times) / len(times)


def main() -> None:
    # Generate data
    data = generate_data(N_ROWS)
    args = (data["close"], data["high"], data["low"], data["volume"])

    # Template detection
    optimizer = DefaultTemplateOptimizer()
    checker = DefaultEquivalenceChecker()
    detected = optimizer.detect_applicable_templates(source_code)

    print(SEP)
    print("TEMPLATE DETECTION")
    print(SEP)
    print(f"Source: compute_risk_scores ({len(source_code)} chars)")
    print(f"Detected templates: {detected}")

    # Benchmark original baseline
    print(SEP)
    print("ORIGINAL BASELINE")
    print(SEP)
    original_output = compute_risk_scores(*args)
    original_ms = benchmark(compute_risk_scores, *args)
    print(f"Time: {original_ms:.2f} ms ({ITERATIONS} iterations)")
    print(f"Output length: {len(original_output)}, mean: {np.mean(original_output):.2f}")

    # Test each detected template
    results: list[dict] = []
    for tmpl_name in detected:
        print(SEP)
        print(f"TEMPLATE: {tmpl_name}")
        print(SEP)
        try:
            optimized_source = optimizer.apply_template(source_code, tmpl_name)
            lines = optimized_source.strip().split("\n")
            print("Transformed code (first 10 lines):")
            for line in lines[:10]:
                print(f"  {line}")
            if len(lines) > 10:
                print(f"  ... ({len(lines) - 10} more lines)")

            # exec the transformed source to extract the function
            namespace = {"np": np, "numba": numba}
            exec(optimized_source, namespace)
            func = namespace["compute_risk_scores"]

            # Run once to trigger JIT (if numba)
            func(*args)

            # Benchmark
            opt_ms = benchmark(func, *args, warmup=1)
            opt_output = func(*args)

            # Check equivalence
            equiv, reason = checker.check_equivalence(original_output, opt_output)
            speedup = original_ms / opt_ms if opt_ms > 0 else 0.0
            correctness = "PASS" if equiv else f"FAIL: {reason}"

            results.append(
                {
                    "name": f"arwiz {tmpl_name}",
                    "ms": opt_ms,
                    "speedup": speedup,
                    "correctness": correctness,
                    "error": None,
                }
            )
            print(f"Time: {opt_ms:.2f} ms, Speedup: {speedup:.1f}x, Correctness: {correctness}")

        except Exception as exc:
            print(f"FAILED: {type(exc).__name__}: {exc}")
            results.append(
                {
                    "name": f"arwiz {tmpl_name}",
                    "ms": None,
                    "speedup": None,
                    "correctness": "FAILED",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    # Hand-written numba variant
    print(SEP)
    print("HAND-WRITTEN NUMBA")
    print(SEP)
    # Warmup (JIT compile)
    _ = compute_risk_scores_numba(*args)
    numba_ms = benchmark(compute_risk_scores_numba, *args, warmup=1)
    numba_output = compute_risk_scores_numba(*args)
    equiv, reason = checker.check_equivalence(original_output, numba_output.tolist())
    numba_speedup = original_ms / numba_ms if numba_ms > 0 else 0.0
    numba_correctness = "PASS" if equiv else f"FAIL: {reason}"
    print(
        f"Time: {numba_ms:.2f} ms, Speedup: {numba_speedup:.1f}x, Correctness: {numba_correctness}"
    )

    # Results summary table
    print(SEP)
    print("RESULTS SUMMARY")
    print(SEP)
    header = f"{'Variant':<25} | {'Time (ms)':>9} | {'Speedup':>8} | {'Correctness':<12}"
    print(header)
    print("-" * len(header))
    print(f"{'Original (baseline)':<25} | {original_ms:>9.2f} | {'1.0x':>8} | {'n/a':<12}")
    for r in results:
        if r["ms"] is not None:
            name, ms, sp, cor = r["name"], r["ms"], r["speedup"], r["correctness"]
            print(f"{name:<25} | {ms:>9.2f} | {sp:>7.1f}x | {cor:<12}")
        else:
            name = r["name"]
            print(f"{name:<25} | {'FAILED':>9} | {'n/a':>8} | {'n/a':<12}")
    print(
        f"{'Hand-written numba':<25} | {numba_ms:>9.2f} | "
        f"{numba_speedup:>7.1f}x | {numba_correctness:<12}"
    )

    # Key observations
    print(SEP)
    print("KEY OBSERVATIONS")
    print(SEP)
    print(f"- Templates detected: {detected}")
    print("- vectorize_loop only transforms trivial accumulator/list-append patterns.")
    print("  compute_risk_scores has complex loop logic (continue, slicing, conditionals),")
    print("  so vectorize_loop returns the function unchanged.")
    print("- numba_jit simply adds @numba.njit decorator without rewriting the body.")
    print("  The original function uses np.clip on a scalar, which fails in numba nopython mode.")
    print("- Hand-written numba shows significant speedup because it was rewritten for")
    print("  numba compatibility (returns array, manual clamp, no list.append).")


if __name__ == "__main__":
    main()

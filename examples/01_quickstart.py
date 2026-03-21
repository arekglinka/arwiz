# Quickstart: profiling a naive loop with arwiz
#
# This script computes a sum of squares using a plain Python for-loop.
# The bottleneck is obvious: the loop runs 100k iterations without
# any vectorization. arwiz will flag `compute_sum` as the hotspot.
#
# Profile it:
#   uv run arwiz profile examples/01_quickstart.py
#
# Optimize the hotspot:
#   uv run arwiz optimize examples/01_quickstart.py --function compute_sum
#
# Trace branch coverage:
#   uv run arwiz coverage examples/01_quickstart.py

import time


def compute_sum(data: list[float]) -> float:
    result = 0.0
    for x in data:
        result += x * x
    return result


def compute_filtered_sum(data: list[float], threshold: float) -> float:
    result = 0.0
    for x in data:
        if x > threshold:
            result += x * x
    return result


def main() -> None:
    data = [float(i) * 0.01 for i in range(100_000)]
    threshold = 500.0

    start = time.perf_counter()
    total = compute_sum(data)
    elapsed = time.perf_counter() - start
    print(f"Sum of squares: {total:.2f}")
    print(f"compute_sum took {elapsed:.4f}s")

    start = time.perf_counter()
    filtered = compute_filtered_sum(data, threshold)
    elapsed = time.perf_counter() - start
    print(f"Filtered sum (> {threshold}): {filtered:.2f}")
    print(f"compute_filtered_sum took {elapsed:.4f}s")


if __name__ == "__main__":
    main()

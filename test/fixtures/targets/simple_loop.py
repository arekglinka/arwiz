"""Simple for-loop script for optimization testing.

This script computes a sum using a naive for loop,
making it an ideal candidate for numpy vectorization.
"""

import time


def compute_sum(data):
    """Compute sum of squares using a naive for loop."""
    result = 0.0
    for x in data:
        result += x * x
    return result


def main():
    data = list(range(10000))
    start = time.perf_counter()
    result = compute_sum(data)
    elapsed = time.perf_counter() - start
    print(f"Result: {result}")
    print(f"Time: {elapsed:.4f}s")
    return result


if __name__ == "__main__":
    main()

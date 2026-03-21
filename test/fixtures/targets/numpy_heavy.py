"""NumPy-heavy computation script for optimization testing.

This script uses NumPy arrays with element-wise operations
that could benefit from further vectorization or Numba JIT.
"""

import time

import numpy as np


def moving_average(data, window=10):
    """Compute moving average using explicit loop (slow)."""
    result = np.zeros(len(data) - window + 1)
    for i in range(len(result)):
        result[i] = np.mean(data[i : i + window])
    return result


def compute_correlation(a, b):
    """Compute Pearson correlation manually (slow)."""
    n = len(a)
    mean_a = np.mean(a)
    mean_b = np.mean(b)
    cov = 0.0
    var_a = 0.0
    var_b = 0.0
    for i in range(n):
        cov += (a[i] - mean_a) * (b[i] - mean_b)
        var_a += (a[i] - mean_a) ** 2
        var_b += (b[i] - mean_b) ** 2
    return cov / (np.sqrt(var_a) * np.sqrt(var_b))


def main():
    data = np.random.randn(10000)
    start = time.perf_counter()
    ma = moving_average(data, window=50)
    corr = compute_correlation(data[:-1], data[1:])
    elapsed = time.perf_counter() - start
    print(f"Moving average shape: {ma.shape}")
    print(f"Correlation: {corr:.6f}")
    print(f"Time: {elapsed:.4f}s")


if __name__ == "__main__":
    main()

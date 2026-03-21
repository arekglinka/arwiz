"""Script with nested function calls for profiling testing.

This script has multiple levels of function calls
to test profiling call tree detection.
"""

import time


def level_3(x):
    """Innermost function."""
    return x**2 + x


def level_2(x):
    """Middle function calling level_3."""
    result = 0
    for i in range(x):
        result += level_3(i)
    return result


def level_1(n):
    """Top-level function calling level_2."""
    return level_2(n) + level_2(n // 2)


def main():
    start = time.perf_counter()
    result = level_1(500)
    elapsed = time.perf_counter() - start
    print(f"Result: {result}")
    print(f"Time: {elapsed:.4f}s")
    return result


if __name__ == "__main__":
    main()

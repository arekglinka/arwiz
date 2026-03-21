"""I/O-bound script for testing batch optimization.

This script performs many small file writes that could
benefit from batching.
"""

import contextlib
import os
import tempfile
import time

TEMP_DIR = tempfile.gettempdir()


def write_results_individually(results, base_name="arwiz_test"):
    """Write each result to a separate file (slow pattern)."""
    paths = []
    for i, result in enumerate(results):
        path = os.path.join(TEMP_DIR, f"{base_name}_{i}.txt")
        with open(path, "w") as f:
            f.write(str(result))
        paths.append(path)
    return paths


def cleanup_files(paths):
    """Remove temporary files."""
    for path in paths:
        with contextlib.suppress(OSError):
            os.remove(path)


def main():
    results = [f"result_{i}: {i**2}" for i in range(100)]
    start = time.perf_counter()
    paths = write_results_individually(results)
    elapsed = time.perf_counter() - start
    print(f"Wrote {len(paths)} files")
    print(f"Time: {elapsed:.4f}s")
    cleanup_files(paths)
    print("Cleaned up")


if __name__ == "__main__":
    main()

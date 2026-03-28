# Baseline: naive loop-based risk score computation (numpy-only, no pandas)
#
# Computes per-bar risk scores from OHLCV data using a sliding window.
# Intentionally uses a Python for-loop with list.append — the pattern
# arwiz's vectorize_loop template targets.
#
# Profile it:
#   uv run arwiz profile examples/05_pandas_baseline.py
#
# Optimize the hotspot:
#   uv run arwiz optimize examples/05_pandas_baseline.py --function compute_risk_scores
#
# Compare all variants (original / arwiz-template / hand-optimized numba):
#   uv run python examples/06_arwiz_comparison.py

import time

import numpy as np


def generate_data(n: int = 500) -> dict[str, np.ndarray]:
    """Generate synthetic OHLCV data as plain numpy arrays."""
    rng = np.random.default_rng(42)
    close = 100.0 + rng.standard_normal(n).cumsum() * 0.1
    high = close + rng.uniform(0, 1, size=n)
    low = close - rng.uniform(0, 1, size=n)
    volume = rng.integers(100, 10_000, size=n).astype(np.float64)
    return {"close": close, "high": high, "low": low, "volume": volume}


def compute_risk_scores(
    closes: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    volumes: np.ndarray,
    window: int = 20,
) -> list[float]:
    """Compute risk scores using a naive Python for-loop with list.append.

    This is the baseline that arwiz templates will attempt to optimize.
    """
    scores: list[float] = []
    for i in range(len(closes)):
        start = max(0, i - window)
        if i - start < 2:
            scores.append(50.0)
            continue

        slice_close = closes[start:i]
        slice_high = highs[start:i]
        slice_low = lows[start:i]
        slice_vol = volumes[start:i]

        mean_c = np.mean(slice_close)
        std_c = np.std(slice_close)

        if std_c < 1e-10:
            scores.append(50.0)
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

        scores.append(float(np.clip(score, 0.0, 100.0)))
    return scores


def main() -> None:
    N = 500
    data = generate_data(N)

    start = time.perf_counter()
    scores = compute_risk_scores(data["close"], data["high"], data["low"], data["volume"])
    elapsed = time.perf_counter() - start

    print(f"Computed {len(scores)} risk scores in {elapsed:.4f}s")
    print(f"Mean score: {np.mean(scores):.2f}, Std: {np.std(scores):.2f}")


if __name__ == "__main__":
    main()

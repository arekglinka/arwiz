# Real-world data processing script with common pandas anti-patterns
#
# Patterns arwiz can detect and improve:
#   - iterrows() for row-by-row transformation (slow)
#   - apply() with a lambda that could be vectorized
#   - Individual file writes in a loop (slow I/O)
#
# Profile it:
#   uv run arwiz profile examples/02_real_world.py
#
# Optimize a specific function:
#   uv run arwiz optimize examples/02_real_world.py \
#       --function add_derived_columns
#
# Trace branch coverage:
#   uv run arwiz coverage examples/02_real_world.py

import time
from pathlib import Path

import numpy as np
import pandas as pd


def generate_data(n: int = 10_000) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    regions = ["North", "South", "East", "West"]
    categories = ["Electronics", "Clothing", "Food", "Books"]
    return pd.DataFrame(
        {
            "order_id": range(1, n + 1),
            "region": rng.choice(regions, size=n),
            "category": rng.choice(categories, size=n),
            "price": rng.uniform(5, 500, size=n),
            "quantity": rng.integers(1, 20, size=n),
            "discount_pct": rng.uniform(0, 0.3, size=n),
        }
    )


def add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add computed columns using iterrows (intentionally slow)."""
    rows = []
    for _, row in df.iterrows():
        revenue = row["price"] * row["quantity"]
        rows.append(
            {
                **row.to_dict(),
                "revenue": revenue,
                "discounted_revenue": revenue * (1 - row["discount_pct"]),
            }
        )
    return pd.DataFrame(rows)


def classify_revenue(row: pd.Series) -> str:
    rev = row["price"] * row["quantity"]
    if rev > 5000:
        return "high"
    if rev > 1000:
        return "medium"
    return "low"


def add_tier_column(df: pd.DataFrame) -> pd.DataFrame:
    """Add a revenue tier column using apply (slower than vectorized)."""
    df = df.copy()
    df["tier"] = df.apply(classify_revenue, axis=1)
    return df


def write_region_reports(df: pd.DataFrame, out_dir: str = "output") -> None:
    """Write one CSV per region (individual I/O in a loop)."""
    path = Path(out_dir)
    path.mkdir(exist_ok=True)
    for region in df["region"].unique():
        df[df["region"] == region].to_csv(path / f"{region.lower()}_report.csv", index=False)
    print(f"Wrote {len(df['region'].unique())} region reports to {out_dir}/")


def main() -> None:
    print("Generating 10k rows of sales data...")
    df = generate_data(10_000)
    print(f"Raw shape: {df.shape}")

    start = time.perf_counter()
    df = add_derived_columns(df)
    print(f"Derived columns added in {time.perf_counter() - start:.2f}s")

    start = time.perf_counter()
    df = add_tier_column(df)
    print(f"Tier column added in {time.perf_counter() - start:.2f}s")

    summary = df.groupby("region")["discounted_revenue"].agg(["mean", "sum", "count"])
    print("\nRevenue summary by region:")
    print(summary.round(2))

    start = time.perf_counter()
    write_region_reports(df)
    print(f"Reports written in {time.perf_counter() - start:.2f}s")


if __name__ == "__main__":
    main()

"""Script with complex branching for coverage testing.

This script has multiple conditional branches to test
branch coverage detection.
"""



def classify_value(x):
    """Classify a numeric value into categories."""
    if x < 0:
        return "negative"
    elif x == 0:
        return "zero"
    elif x < 10:
        return "small"
    elif x < 100:
        return "medium"
    else:
        return "large"


def process_data(data):
    """Process data with multiple branch paths."""
    results = []
    for item in data:
        category = classify_value(item)
        if category in ("negative", "zero"):
            results.append(0)
        elif category == "small":
            results.append(item * 2)
        elif category == "medium":
            results.append(item * 3)
        else:
            results.append(item * 4)
    return results


def fibonacci(n):
    """Compute fibonacci with branching."""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


def main():
    test_data = [-5, 0, 3, 50, 200]
    results = process_data(test_data)
    print(f"Results: {results}")
    fib = fibonacci(10)
    print(f"Fibonacci(10): {fib}")


if __name__ == "__main__":
    main()

"""Shared fixtures for target script tests."""

from __future__ import annotations

from pathlib import Path

import pytest


TARGETS_DIR = Path(__file__).parent / "targets"

TARGET_NAMES = [
    "simple_loop",
    "nested_calls",
    "numpy_heavy",
    "io_bound",
    "branching",
]


@pytest.fixture(params=TARGET_NAMES, scope="session")
def target_name(request):
    """Yield each target script name."""
    return request.param


@pytest.fixture(scope="session")
def targets_dir():
    """Path to the targets directory."""
    return TARGETS_DIR


@pytest.fixture(scope="session")
def target_scripts():
    """Dict mapping target name -> Path."""
    return {name: TARGETS_DIR / f"{name}.py" for name in TARGET_NAMES}


@pytest.fixture(scope="session")
def target_paths(target_scripts):
    """List of all target script Paths."""
    return list(target_scripts.values())


@pytest.fixture(scope="session")
def sample_data():
    """Sample data matching what target scripts use internally."""
    return list(range(100))


@pytest.fixture(scope="session")
def sample_numpy_data():
    """Small numpy array for testing."""
    import numpy as np

    return np.arange(100, dtype=float)

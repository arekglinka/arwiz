"""Tests for target script fixtures.

Validates that all target scripts exist, are valid Python,
and their main() functions are importable.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from .conftest import TARGETS_DIR, TARGET_NAMES


class TestTargetPathsExist:
    """Verify each target script file exists."""

    @pytest.mark.parametrize("name", TARGET_NAMES)
    def test_target_file_exists(self, name):
        path = TARGETS_DIR / f"{name}.py"
        assert path.exists(), f"Target script {name}.py not found at {path}"

    @pytest.mark.parametrize("name", TARGET_NAMES)
    def test_target_file_is_file(self, name):
        path = TARGETS_DIR / f"{name}.py"
        assert path.is_file(), f"{path} is not a regular file"


class TestTargetScriptsAreValidPython:
    """Verify each target script compiles without syntax errors."""

    @pytest.mark.parametrize("name", TARGET_NAMES)
    def test_compile_check(self, name):
        path = TARGETS_DIR / f"{name}.py"
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")


class TestTargetMainImportable:
    """Verify each target script's main() is importable and callable."""

    @pytest.mark.parametrize("name", TARGET_NAMES)
    def test_main_callable(self, name, tmp_path, monkeypatch):
        """Import each target module and assert main is callable.

        For io_bound, monkeypatch write operations to avoid actual I/O.
        """
        path = TARGETS_DIR / f"{name}.py"
        spec = importlib.util.spec_from_file_location(f"targets.{name}", path)
        assert spec is not None, f"Could not create module spec for {name}"
        assert spec.loader is not None, f"Spec has no loader for {name}"

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        assert hasattr(module, "main"), f"{name} module has no main() function"
        assert callable(module.main), f"{name}.main is not callable"

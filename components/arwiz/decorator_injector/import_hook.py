"""Alternative import-time decorator injection via sys.meta_path hook."""

from __future__ import annotations

import contextlib
import importlib.abc
import importlib.machinery
import sys
import warnings
from typing import Any


class ArwizImportFinder(importlib.abc.MetaPathFinder):
    """Meta path finder that logs intercepted imports for decorator injection.

    This is an alternative to source rewriting. Instead of modifying files
    on disk, it intercepts module imports and can inject decorators at import
    time. Currently implements a logging-only mode; full injection is a
    future enhancement.
    """

    def __init__(self, decorator_name: str, target_modules: set[str] | None = None) -> None:
        self.decorator_name = decorator_name
        self.target_modules = target_modules
        self.intercepted: list[str] = []

    def find_spec(
        self,
        fullname: str,
        path: Any = None,
        target: Any = None,
    ) -> importlib.machinery.ModuleSpec | None:
        if self.target_modules is None or fullname in self.target_modules:
            self.intercepted.append(fullname)
            warnings.warn(
                f"[arwiz] Import intercepted: {fullname}",
                stacklevel=3,
            )
        return None


def install_import_hook(
    decorator_name: str = "arwiz_capture",
    target_modules: set[str] | None = None,
) -> ArwizImportFinder:
    """Install an ArwizImportFinder into sys.meta_path.

    Args:
        decorator_name: Name of the decorator to inject.
        target_modules: Optional set of module names to intercept.

    Returns:
        The finder instance, for later removal via uninstall_import_hook.
    """
    finder = ArwizImportFinder(decorator_name, target_modules)
    sys.meta_path.insert(0, finder)
    return finder


def uninstall_import_hook(finder: ArwizImportFinder) -> None:
    """Remove an ArwizImportFinder from sys.meta_path."""
    with contextlib.suppress(ValueError):
        sys.meta_path.remove(finder)

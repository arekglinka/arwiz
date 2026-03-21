"""Architecture tests to validate Polylith structure and dependency rules for arwiz."""

import ast
from pathlib import Path

import pytest

NAMESPACE = "arwiz"
PROJECT_ROOT = Path(__file__).parent.parent
COMPONENTS_NS = PROJECT_ROOT / "components" / NAMESPACE
BASES_NS = PROJECT_ROOT / "bases" / NAMESPACE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _python_files(root: Path) -> list[Path]:
    """Return all .py files recursively under *root*."""
    if not root.is_dir():
        return []
    return [p for p in root.rglob("*.py") if p.is_file()]


def _parse_imports(path: Path) -> set[str]:
    """Return top-level module names imported in *path* via AST."""
    with open(path) as f:
        tree = ast.parse(f.read())
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    return imports


def _iter_from_imports(path: Path) -> list[str]:
    """Return full module strings from ``from X import ...`` statements."""
    with open(path) as f:
        tree = ast.parse(f.read())
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules


def _component_dirs() -> list[Path]:
    """Return component directories (excl. foundation, hidden dirs)."""
    if not COMPONENTS_NS.is_dir():
        return []
    return [
        d
        for d in COMPONENTS_NS.iterdir()
        if d.is_dir() and not d.name.startswith("_") and d.name != "foundation"
    ]


def _has_components() -> bool:
    return COMPONENTS_NS.is_dir() and any(
        d.is_dir() and not d.name.startswith("_") for d in COMPONENTS_NS.iterdir()
    )


# ---------------------------------------------------------------------------
# 1. PEP 420 – No namespace __init__.py
# ---------------------------------------------------------------------------


class TestPEP420Compliance:
    """Verify PEP 420 namespace package rules."""

    def test_no_namespace_init_files(self) -> None:
        """bases/arwiz/ and components/arwiz/ must NOT contain __init__.py."""
        violations: list[str] = []

        for ns_dir in (COMPONENTS_NS, BASES_NS):
            init_file = ns_dir / "__init__.py"
            if init_file.exists():
                violations.append(str(init_file))

        assert not violations, (
            f"PEP 420 violation: __init__.py found in namespace dirs: {violations}. "
            f"Namespace packages must NOT have __init__.py — delete these files."
        )


# ---------------------------------------------------------------------------
# 2. Foundation – zero external dependencies
# ---------------------------------------------------------------------------


class TestFoundationDependencies:
    """Foundation layer must have minimal/zero external dependencies."""

    @pytest.fixture
    def foundation_paths(self) -> list[Path]:
        return _python_files(COMPONENTS_NS / "foundation")

    @pytest.mark.skipif(
        not (COMPONENTS_NS / "foundation").is_dir(),
        reason="Foundation component not yet created",
    )
    def test_foundation_imports_only_stdlib_and_pydantic(
        self, foundation_paths: list[Path]
    ) -> None:
        """Foundation should only import stdlib + pydantic (no numpy, pandas, click, etc.)."""
        allowed_stdlib = {
            "datetime",
            "enum",
            "typing",
            "pathlib",
            "abc",
            "dataclasses",
            "collections",
            "contextlib",
            "functools",
            "itertools",
            "re",
            "json",
            "os",
            "sys",
            "hashlib",
            "time",
            "logging",
            "warnings",
            "struct",
            "io",
            "copy",
            "math",
            "statistics",
            "operator",
            "textwrap",
            "ast",
            "importlib",
            "__future__",
        }
        allowed_external = {
            "pydantic",
        }

        for path in foundation_paths:
            if path.name.startswith("test_"):
                continue

            imports = _parse_imports(path)

            for imp in imports:
                if imp == NAMESPACE:
                    continue  # Internal namespace imports are fine
                if imp.startswith("components"):
                    continue
                if imp in allowed_stdlib:
                    continue
                if imp in allowed_external:
                    continue
                pytest.fail(
                    f"Foundation module {path} has disallowed import: {imp}. "
                    f"Foundation should only use stdlib + pydantic, not external packages."
                )

    @pytest.mark.skipif(
        not (COMPONENTS_NS / "foundation").is_dir(),
        reason="Foundation component not yet created",
    )
    def test_foundation_no_implementation_dependencies(self, foundation_paths: list[Path]) -> None:
        """Foundation must not depend on other components."""
        for path in foundation_paths:
            if path.name.startswith("test_"):
                continue

            for module in _iter_from_imports(path):
                if module.startswith(f"{NAMESPACE}."):
                    parts = module.split(".")
                    if len(parts) >= 2:
                        component_name = parts[1]
                        if component_name != "foundation":
                            pytest.fail(
                                f"Foundation module {path} imports from component "
                                f"'{component_name}'. Foundation must not depend on other "
                                f"{NAMESPACE} components."
                            )


# ---------------------------------------------------------------------------
# 3. Component interface–core separation
# ---------------------------------------------------------------------------


class TestComponentInterfaceSeparation:
    """Components must use interface-implementation pattern."""

    @pytest.mark.skipif(not _has_components(), reason="No components exist yet")
    def test_components_import_interfaces_not_cores(self) -> None:
        """Components should import from interfaces, not core implementations of other components."""
        component_dirs = _component_dirs()
        component_names = {d.name for d in component_dirs}

        for comp_dir in component_dirs:
            for py_file in comp_dir.rglob("*.py"):
                if py_file.name in ("__init__.py", "interface.py") or py_file.name.startswith(
                    "test_"
                ):
                    continue

                for module in _iter_from_imports(py_file):
                    if not module.startswith(f"{NAMESPACE}."):
                        continue
                    parts = module.split(".")
                    if len(parts) >= 3:
                        target_component = parts[1]
                        import_type = parts[2]

                        if target_component in component_names and import_type == "core":
                            pytest.fail(
                                f"File {py_file} imports from {module}. "
                                f"Should import from {NAMESPACE}.{target_component}.interface instead."
                            )


# ---------------------------------------------------------------------------
# 4. Dependency direction
# ---------------------------------------------------------------------------


class TestDependencyDirection:
    """Dependencies must flow: bases → components → foundation."""

    def test_bases_import_only_interfaces(self) -> None:
        """Bases must only import component interfaces, never core implementations."""
        if not BASES_NS.is_dir():
            pytest.skip("No bases directory yet")

        for py_file in BASES_NS.rglob("*.py"):
            if py_file.name == "__init__.py" or py_file.name.startswith("test_"):
                continue

            for module in _iter_from_imports(py_file):
                if not module.startswith(f"{NAMESPACE}."):
                    continue
                parts = module.split(".")
                if len(parts) >= 3 and parts[2] == "core":
                    pytest.fail(
                        f"File {py_file} imports from {module}. "
                        f"Bases should import from component interfaces "
                        f"({NAMESPACE}.X.interface), not implementations ({NAMESPACE}.X.core)."
                    )

    @pytest.mark.skipif(not _has_components(), reason="No components exist yet")
    def test_components_can_import_foundation(self) -> None:
        """Components may import from foundation — this test documents the rule."""
        component_dirs = _component_dirs()
        # This test always passes; it exists as documentation that components
        # importing foundation is ALLOWED.
        assert True


# ---------------------------------------------------------------------------
# 5. Circular dependency detection
# ---------------------------------------------------------------------------


class TestNoCircularDependencies:
    """Detect circular dependencies between components."""

    @pytest.mark.skipif(not _has_components(), reason="No components exist yet")
    def test_no_circular_component_dependencies(self) -> None:
        """Build import graph and detect cycles via DFS."""
        component_dirs = _component_dirs()
        component_names = {d.name for d in component_dirs}
        import_graph: dict[str, set[str]] = {d.name: set() for d in component_dirs}

        for comp_dir in component_dirs:
            for py_file in comp_dir.rglob("*.py"):
                if py_file.name == "__init__.py" or py_file.name.startswith("test_"):
                    continue

                for module in _iter_from_imports(py_file):
                    if not module.startswith(f"{NAMESPACE}."):
                        continue
                    parts = module.split(".")
                    if len(parts) >= 2:
                        target = parts[1]
                        if target in component_names and target != comp_dir.name:
                            import_graph[comp_dir.name].add(target)

        def _has_cycle(
            graph: dict[str, set[str]],
            node: str,
            visited: set[str],
            rec_stack: set[str],
        ) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if _has_cycle(graph, neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(node)
            return False

        visited: set[str] = set()
        for component in import_graph:
            if component not in visited and _has_cycle(import_graph, component, visited, set()):
                pytest.fail(
                    f"Circular dependency detected involving component '{component}'. "
                    f"Dependencies must be acyclic."
                )


# ---------------------------------------------------------------------------
# 6. Interface complexity (Interface Segregation Principle)
# ---------------------------------------------------------------------------


class TestInterfaceComplexity:
    """Interfaces must maintain appropriate complexity."""

    def _interface_classes(self) -> dict[str, list[str]]:
        """Return {component.ClassName: [public_methods]} for all interface files."""
        if not COMPONENTS_NS.is_dir():
            return {}

        result: dict[str, list[str]] = {}
        for path in COMPONENTS_NS.rglob("interface.py"):
            with open(path) as f:
                tree = ast.parse(f.read())

            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue

                is_dataclass = any(
                    (isinstance(dec, ast.Name) and dec.id == "dataclass")
                    or (
                        isinstance(dec, ast.Call)
                        and isinstance(dec.func, ast.Name)
                        and dec.func.id == "dataclass"
                    )
                    for dec in node.decorator_list
                )
                if is_dataclass:
                    continue

                methods = [
                    n.name
                    for n in node.body
                    if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")
                ]
                result[f"{path.parent.name}.{node.name}"] = methods

        return result

    @pytest.mark.skipif(not _has_components(), reason="No components exist yet")
    def test_interfaces_not_too_complex(self) -> None:
        """Interfaces should have <= 10 public methods."""
        for class_name, methods in self._interface_classes().items():
            if len(methods) > 10:
                pytest.fail(
                    f"Interface {class_name} has {len(methods)} public methods. "
                    f"Consider splitting into multiple interfaces "
                    f"(Interface Segregation Principle)."
                )

    @pytest.mark.skipif(not _has_components(), reason="No components exist yet")
    def test_interfaces_have_at_least_one_method(self) -> None:
        """Non-dataclass interface classes should have at least one public method."""
        for class_name, methods in self._interface_classes().items():
            if not methods:
                pytest.fail(
                    f"Interface {class_name} has no public methods. "
                    f"Consider removing it or adding methods."
                )

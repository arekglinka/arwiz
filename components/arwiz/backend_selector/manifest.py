import importlib.util
from importlib import import_module
from typing import Any


class BackendManifest:
    def __init__(self) -> None:
        self._backend_info_cls = import_module("arwiz.foundation").BackendInfo
        self._manifest = self._build_default_manifest()
        self._availability_cache: dict[str, tuple[bool, str | None]] = {}

    def _build_default_manifest(self) -> dict[str, Any]:
        backend_info = self._backend_info_cls
        return {
            "numba": backend_info(
                name="numba",
                tier=1,
                strengths=[
                    "JIT compilation",
                    "nopython mode",
                    "no build step required",
                    "easy to use",
                ],
                limitations=[
                    "no Python objects in nopython",
                    "limited string support",
                    "limited C interop",
                ],
                ast_patterns=["for_loop", "numeric_ops", "numpy_calls", "nested_loops"],
                best_for=["small arrays <1K elements", "pure numeric loops", "quick prototyping"],
                performance_range=(10.0, 200.0),
                install_hint="pip install numba",
            ),
            "cython": backend_info(
                name="cython",
                tier=1,
                strengths=[
                    "CPU parallelism",
                    "typed memoryviews",
                    "complex control flow",
                    "AOT compilation",
                ],
                limitations=[
                    "requires C compiler",
                    "AOT compilation step",
                    "learning curve",
                ],
                ast_patterns=["for_loop", "nested_loops", "array_indexing", "numeric_ops"],
                best_for=["medium arrays 1K-100K", "complex control flow", "mixed Python/C code"],
                performance_range=(10.0, 100.0),
                install_hint="pip install cython",
            ),
            "jax": backend_info(
                name="jax",
                tier=2,
                strengths=[
                    "XLA JIT compilation",
                    "GPU/TPU support",
                    "autodiff",
                    "drop-in numpy API (jnp)",
                ],
                limitations=[
                    "GPU overhead for small arrays",
                    "no in-place operations",
                    "JIT trace limitations",
                ],
                ast_patterns=["numpy_calls", "vectorizable_ops", "array_operations"],
                best_for=["large arrays >100K", "differentiable computation", "GPU parallelism"],
                performance_range=(5.0, 100.0),
                install_hint="pip install jax jaxlib",
            ),
            "cupy": backend_info(
                name="cupy",
                tier=2,
                strengths=[
                    "drop-in numpy replacement for GPU",
                    "CUDA kernels",
                    "large array speedup",
                ],
                limitations=[
                    "NVIDIA GPU required",
                    "GPU transfer overhead",
                    "~1-2s import time",
                ],
                ast_patterns=["numpy_calls", "large_array_ops", "array_operations"],
                best_for=["large arrays >100K on GPU", "drop-in numpy replacement"],
                performance_range=(10.0, 100.0),
                install_hint="pip install cupy-cuda12x",
            ),
            "numexpr": backend_info(
                name="numexpr",
                tier=2,
                strengths=["no compilation needed", "threaded evaluation", "trivial integration"],
                limitations=["only arithmetic expressions", "max 64 operands", "no control flow"],
                ast_patterns=["arithmetic_expressions", "numpy_broadcasting"],
                best_for=["element-wise arithmetic on arrays", "quick wins with minimal changes"],
                performance_range=(2.0, 15.0),
                install_hint="pip install numexpr",
            ),
            "pyo3": backend_info(
                name="pyo3",
                tier=3,
                strengths=[
                    "max single-thread performance",
                    "no GC overhead",
                    "memory safety",
                    "string processing",
                ],
                limitations=[
                    "requires Rust toolchain",
                    "complex build process",
                    "steep learning curve",
                ],
                ast_patterns=[
                    "string_operations",
                    "nested_loops",
                    "complex_logic",
                    "memory_operations",
                ],
                best_for=[
                    "string processing",
                    "max single-thread performance",
                    "multi-core with Rayon",
                ],
                performance_range=(10.0, 200.0),
                install_hint="pip install maturin",
            ),
            "cffi": backend_info(
                name="cffi",
                tier=3,
                strengths=["runtime C compilation", "dynamic C integration", "ffi.verify()"],
                limitations=[
                    "requires C code generation",
                    "platform-specific",
                    "limited Python integration",
                ],
                ast_patterns=["c_api_calls", "memory_operations"],
                best_for=["calling existing C libraries", "dynamic C integration"],
                performance_range=(5.0, 50.0),
                install_hint="pip install cffi",
            ),
            "taichi": backend_info(
                name="taichi",
                tier=3,
                strengths=["GPU spatial computation", "physical simulation acceleration"],
                limitations=[
                    "Python 3.11+ incompatible",
                    "GPU required",
                    "limited language subset",
                ],
                ast_patterns=[],
                best_for=["physical simulation", "spatial computation"],
                performance_range=(10.0, 500.0),
                is_available=False,
                availability_reason="Taichi requires Python <=3.10, project uses Python 3.12+",
                install_hint="pip install taichi (requires Python <=3.10)",
            ),
        }

    def check_availability(self, name: str) -> tuple[bool, str | None]:
        if name in self._availability_cache:
            return self._availability_cache[name]

        if name not in self._manifest:
            result = (False, f"Backend '{name}' is not registered")
            self._availability_cache[name] = result
            return result

        if name == "taichi":
            result = (False, "Taichi requires Python <=3.10, project uses Python 3.12+")
            self._availability_cache[name] = result
            return result

        is_available = importlib.util.find_spec(name) is not None
        reason = None if is_available else f"Backend '{name}' is not installed"
        result = (is_available, reason)
        self._availability_cache[name] = result
        return result

    def get_backend(self, name: str) -> Any:
        return self._manifest[name]

    def all_backends(self) -> dict[str, Any]:
        for name, backend in self._manifest.items():
            is_available, reason = self.check_availability(name)
            backend.is_available = is_available
            backend.availability_reason = reason
        return self._manifest

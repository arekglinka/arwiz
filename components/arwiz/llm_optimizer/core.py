from typing import Any
from uuid import uuid4

import httpx

from ..foundation import HotSpot, LLMConfig, OptimizationAttempt
from .prompts import (
    build_batch_io_prompt,
    build_caching_prompt,
    build_cffi_prompt,
    build_cupy_prompt,
    build_cython_prompt,
    build_jax_prompt,
    build_manifest_context,
    build_numba_jit_prompt,
    build_numba_parallel_prompt,
    build_numexpr_prompt,
    build_pyo3_prompt,
    build_taichi_prompt,
    build_vectorization_prompt,
)
from .providers import get_provider


class DefaultLLMOptimizer:
    def __init__(
        self,
        config: LLMConfig | None = None,
        backend_manifest: Any | None = None,
    ) -> None:
        self.config = config or LLMConfig()
        self.backend_manifest = backend_manifest

    def optimize_function(
        self,
        source_code: str,
        hotspot: HotSpot,
        config: LLMConfig | None = None,
        strategy: str = "auto",
        manifest_context: str | None = None,
    ) -> OptimizationAttempt:
        effective_config = config or self.config
        prompt = self.generate_prompt(
            source_code,
            hotspot,
            strategy=strategy,
            manifest_context=manifest_context,
        )
        provider = getattr(self, "provider", None) or get_provider(effective_config)
        try:
            response = provider.generate(
                prompt,
                effective_config.model,
                max_tokens=effective_config.max_tokens,
                temperature=effective_config.temperature,
            )
        except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.ConnectError) as exc:
            return OptimizationAttempt(
                attempt_id=f"llm_{uuid4().hex[:12]}",
                original_code=source_code,
                optimized_code=source_code,
                strategy="llm_generated",
                llm_model=effective_config.model,
                syntax_valid=False,
                error_message=str(exc),
            )
        except Exception as exc:
            return OptimizationAttempt(
                attempt_id=f"llm_{uuid4().hex[:12]}",
                original_code=source_code,
                optimized_code=source_code,
                strategy="llm_generated",
                llm_model=effective_config.model,
                syntax_valid=False,
                error_message=str(exc),
            )
        optimized_code = self.parse_llm_response(response)
        syntax_valid, error_message = self.validate_syntax(optimized_code)

        return OptimizationAttempt(
            attempt_id=f"llm_{uuid4().hex[:12]}",
            original_code=source_code,
            optimized_code=optimized_code,
            strategy="llm_generated",
            llm_model=effective_config.model,
            syntax_valid=syntax_valid,
            error_message=None if syntax_valid else error_message,
        )

    def generate_prompt(
        self,
        source_code: str,
        hotspot: HotSpot,
        strategy: str = "auto",
        manifest_context: str | None = None,
    ) -> str:
        backend_manifest_context = manifest_context
        normalized = strategy.lower().strip()
        auto_manifest_fallback = False

        if normalized == "manifest_consult":
            normalized = "auto"
            auto_manifest_fallback = True

        if normalized == "auto":
            selected = "vectorize" if "for " in source_code or "while " in source_code else "numba"
            heuristic_confidence = 0.8 if selected == "vectorize" else 0.4
            normalized = selected
            auto_manifest_fallback = heuristic_confidence < 0.5

            if auto_manifest_fallback and not backend_manifest_context:
                backend_manifest_provider = self.backend_manifest
                if backend_manifest_provider is not None:
                    all_backends = backend_manifest_provider.all_backends()
                    backend_manifest_context = build_manifest_context(all_backends)

        profiling_context = (
            f"\nProfiling context:\n"
            f"- function_name: {hotspot.function_name}\n"
            f"- self_time_ms: {hotspot.self_time_ms}\n"
            f"- call_count: {hotspot.call_count}\n"
        )

        manifest_suffix = ""
        if auto_manifest_fallback and backend_manifest_context:
            manifest_suffix = (
                "\nBackend selection context:\n"
                f"{backend_manifest_context}\n"
                "Choose the best backend based on this context and hotspot characteristics.\n"
            )

        if normalized in {"vectorization", "vectorize", "numpy"}:
            hint = "Strategy hint: vectorize loops first, then simplify Python iteration overhead."
            return (
                f"{build_vectorization_prompt(source_code, hotspot)}{profiling_context}\n{hint}\n"
            )
        if normalized in {"numba", "numba_jit", "jit"}:
            hint = (
                "Strategy hint: keep code nopython-friendly "
                "and prefer primitive numeric operations."
            )
            return (
                f"{build_numba_jit_prompt(source_code, hotspot)}{profiling_context}\n{hint}\n"
                f"{manifest_suffix}"
            )
        if normalized in {"numba_parallel", "numba-parallel"}:
            hint = (
                "Strategy hint: only parallelize loops with independent "
                "iterations and replace range with prange where safe."
            )
            return (
                f"{build_numba_parallel_prompt(source_code, hotspot)}{profiling_context}\n{hint}\n"
            )
        if normalized in {"cython", "typed_memoryview"}:
            hint = (
                "Strategy hint: use typed memoryviews and Cython directives "
                "to reduce bounds and wraparound overhead."
            )
            return f"{build_cython_prompt(source_code, hotspot)}{profiling_context}\n{hint}\n"
        if normalized in {"caching", "cache", "memoization"}:
            hint = (
                "Strategy hint: apply caching only when function "
                "output is deterministic for inputs."
            )
            return f"{build_caching_prompt(source_code, hotspot)}{profiling_context}\n{hint}\n"
        if normalized in {"batch_io", "batch-io", "io"}:
            hint = "Strategy hint: reduce syscall frequency by aggregating writes/reads safely."
            return f"{build_batch_io_prompt(source_code, hotspot)}{profiling_context}\n{hint}\n"
        if normalized in {"numexpr", "numexpr-evaluate"}:
            hint = (
                "Strategy hint: target simple element-wise arithmetic expressions "
                "and use numexpr.evaluate for vectorized threaded evaluation."
            )
            return f"{build_numexpr_prompt(source_code, hotspot)}{profiling_context}\n{hint}\n"
        if normalized in {"cupy", "cupy-gpu"}:
            hint = (
                "Strategy hint: transfer data to GPU with cp.asarray, "
                "use CuPy ops, then convert results with cp.asnumpy."
            )
            return f"{build_cupy_prompt(source_code, hotspot)}{profiling_context}\n{hint}\n"
        if normalized in {"jax", "jax_jit"}:
            hint = (
                "Strategy hint: replace NumPy operations with jax.numpy and "
                "use @jax.jit on numerical hotspots for XLA compilation."
            )
            return f"{build_jax_prompt(source_code, hotspot)}{profiling_context}\n{hint}\n"
        if normalized in {"pyo3", "rust"}:
            hint = (
                "Strategy hint: target string-heavy hotspots and generate Rust "
                "PyO3 wrappers with #[pyfunction] and maturin develop build flow."
            )
            return f"{build_pyo3_prompt(source_code, hotspot)}{profiling_context}\n{hint}\n"
        if normalized in {"cffi", "ffi"}:
            hint = (
                "Strategy hint: declare C API with ffi.cdef, compile via ffi.verify, "
                "and keep a safe Python wrapper around C calls."
            )
            return f"{build_cffi_prompt(source_code, hotspot)}{profiling_context}\n{hint}\n"
        if normalized in {"taichi"}:
            return build_taichi_prompt(source_code, hotspot)
        return (
            f"{build_numba_jit_prompt(source_code, hotspot)}{profiling_context}\n"
            "Strategy hint: JIT-compile hotspots.\n"
            f"{manifest_suffix}"
        )

    def parse_llm_response(self, response: str) -> str:
        marker = "```"
        if marker in response:
            parts = response.split(marker)
            for part in parts:
                section = part.strip()
                if section.startswith("python"):
                    code = section[len("python") :].strip()
                    if not code:
                        continue
                    return code
            for part in parts:
                section = part.strip()
                if section and not section.lower().startswith("python"):
                    return section
            return ""

        lines = [line.rstrip() for line in response.strip().splitlines() if line.strip()]
        code_start = next(
            (
                index
                for index, line in enumerate(lines)
                if line.startswith(("def ", "class ", "import ", "from ", "@"))
            ),
            0,
        )
        return "\n".join(lines[code_start:]).strip()

    def validate_syntax(self, code: str) -> tuple[bool, str]:
        try:
            compile(code, "<string>", "exec")
        except SyntaxError as exc:
            return False, str(exc)
        return True, ""

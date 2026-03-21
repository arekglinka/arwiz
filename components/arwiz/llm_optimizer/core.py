from uuid import uuid4

from arwiz.foundation import HotSpot, LLMConfig, OptimizationAttempt
from arwiz.llm_optimizer.prompts import (
    build_batch_io_prompt,
    build_caching_prompt,
    build_numba_jit_prompt,
    build_vectorization_prompt,
)
from arwiz.llm_optimizer.providers import get_provider


class DefaultLLMOptimizer:
    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig()

    def optimize_function(
        self,
        source_code: str,
        hotspot: HotSpot,
        config: LLMConfig | None = None,
    ) -> OptimizationAttempt:
        effective_config = config or self.config
        prompt = self.generate_prompt(source_code, hotspot, strategy="vectorization")
        provider = getattr(self, "provider", None) or get_provider(effective_config)
        response = provider.generate(
            prompt,
            effective_config.model,
            max_tokens=effective_config.max_tokens,
            temperature=effective_config.temperature,
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

    def generate_prompt(self, source_code: str, hotspot: HotSpot, strategy: str = "auto") -> str:
        normalized = strategy.lower().strip()
        if normalized == "auto":
            normalized = (
                "vectorize" if "for " in source_code or "while " in source_code else "numba"
            )

        profiling_context = (
            f"\nProfiling context:\n"
            f"- function_name: {hotspot.function_name}\n"
            f"- self_time_ms: {hotspot.self_time_ms}\n"
            f"- call_count: {hotspot.call_count}\n"
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
            return f"{build_numba_jit_prompt(source_code, hotspot)}{profiling_context}\n{hint}\n"
        if normalized in {"caching", "cache", "memoization"}:
            hint = (
                "Strategy hint: apply caching only when function "
                "output is deterministic for inputs."
            )
            return f"{build_caching_prompt(source_code, hotspot)}{profiling_context}\n{hint}\n"
        if normalized in {"batch_io", "batch-io", "io"}:
            hint = "Strategy hint: reduce syscall frequency by aggregating writes/reads safely."
            return f"{build_batch_io_prompt(source_code, hotspot)}{profiling_context}\n{hint}\n"
        return (
            f"{build_numba_jit_prompt(source_code, hotspot)}{profiling_context}\n"
            "Strategy hint: JIT-compile hotspots.\n"
        )

    def parse_llm_response(self, response: str) -> str:
        marker = "```"
        if marker in response:
            parts = response.split(marker)
            for part in parts:
                section = part.strip()
                if section.startswith("python"):
                    return section[len("python") :].strip()
            for part in parts:
                section = part.strip()
                if section and not section.lower().startswith("python"):
                    return section

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

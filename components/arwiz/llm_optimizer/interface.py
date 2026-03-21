from typing import Protocol

from arwiz.foundation import HotSpot, LLMConfig, OptimizationAttempt


class LLMOptimizerProtocol(Protocol):
    def optimize_function(
        self,
        source_code: str,
        hotspot: HotSpot,
        config: LLMConfig | None = None,
    ) -> OptimizationAttempt: ...

    def generate_prompt(self, source_code: str, hotspot: HotSpot, strategy: str) -> str: ...

    def parse_llm_response(self, response: str) -> str: ...

    def validate_syntax(self, code: str) -> tuple[bool, str]: ...

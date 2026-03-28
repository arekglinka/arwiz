from datetime import UTC, datetime

from pydantic import BaseModel, Field


class OptimizationAttempt(BaseModel):
    attempt_id: str
    original_code: str
    optimized_code: str
    strategy: str
    llm_model: str | None = None
    template_name: str | None = None
    backend: str | None = None
    syntax_valid: bool = False
    passed_equivalence: bool = False
    speedup_percent: float = 0.0
    error_message: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class OptimizationResult(BaseModel):
    function_name: str
    file_path: str
    attempts: list[OptimizationAttempt] = Field(default_factory=list)
    best_attempt: OptimizationAttempt | None = None
    applied: bool = False
    total_time_saved_ms: float = 0.0

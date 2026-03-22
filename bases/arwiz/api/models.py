from pydantic import BaseModel, Field


class ProfileRequest(BaseModel):
    script_path: str
    args: list[str] = Field(default_factory=list)
    timeout: int = 30


class ProfileResponse(BaseModel):
    profile_id: str
    hotspots: list[dict]
    duration_ms: float
    total_calls: int


class OptimizeRequest(BaseModel):
    script_path: str
    function_name: str
    strategy: str = "auto"


class OptimizeResponse(BaseModel):
    class OptimizationAttemptResponse(BaseModel):
        attempt_id: str
        original_code: str
        optimized_code: str
        strategy: str
        llm_model: str | None = None
        template_name: str | None = None
        syntax_valid: bool
        passed_equivalence: bool
        speedup_percent: float
        error_message: str | None = None
        timestamp: str

    function_name: str
    file_path: str
    attempts: list[OptimizationAttemptResponse] = Field(default_factory=list)
    best_attempt: OptimizationAttemptResponse | None = None
    applied: bool
    total_time_saved_ms: float


class CoverageRequest(BaseModel):
    script_path: str
    args: list[str] = Field(default_factory=list)


class CoverageResponse(BaseModel):
    total_branches: int
    covered_branches: int
    coverage_percent: float


class HealthResponse(BaseModel):
    status: str
    version: str

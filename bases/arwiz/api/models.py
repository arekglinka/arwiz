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
    original_code: str
    optimized_code: str
    strategy: str
    syntax_valid: bool


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

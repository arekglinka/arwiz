from pydantic import BaseModel, Field


class InputSnapshot(BaseModel):
    snapshot_id: str
    function_name: str
    args_repr: str
    kwargs_repr: str
    result_repr: str | None = None
    timestamp: str
    content_hash: str
    storage_path: str | None = None


class BranchInfo(BaseModel):
    line_number: int
    branch_type: str
    condition: str
    taken: bool = False


class BranchCoverage(BaseModel):
    total_branches: int
    covered_branches: int
    coverage_percent: float
    uncovered_lines: list[int] = Field(default_factory=list)
    branch_details: list[BranchInfo] = Field(default_factory=list)
    script_path: str
    duration_ms: float

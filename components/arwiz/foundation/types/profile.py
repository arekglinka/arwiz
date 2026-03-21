import time
from datetime import UTC, datetime

from pydantic import BaseModel, Field


class CallNode(BaseModel):
    function_name: str
    file_path: str
    line_number: int
    children: list["CallNode"] = Field(default_factory=list)
    cumulative_time_ms: float = 0.0
    self_time_ms: float = 0.0
    call_count: int = 0


class HotSpot(BaseModel):
    function_name: str
    file_path: str
    line_range: tuple[int, int]
    cumulative_time_ms: float
    self_time_ms: float
    call_count: int = 0
    is_c_extension: bool = False
    potential_speedup: float = 0.0


class ProfileResult(BaseModel):
    profile_id: str = Field(default_factory=lambda: "prof_" + str(time.time_ns()))
    script_path: str
    duration_ms: float
    call_tree: CallNode | None = None
    hotspots: list[HotSpot] = Field(default_factory=list)
    raw_stats_path: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

from pydantic import BaseModel, field_validator


class BackendInfo(BaseModel):
    name: str
    tier: int
    strengths: list[str]
    limitations: list[str]
    ast_patterns: list[str]
    best_for: list[str]
    performance_range: tuple[float, float]
    is_available: bool = True
    availability_reason: str | None = None
    install_hint: str

    @field_validator("tier")
    @classmethod
    def validate_tier(cls, value: int) -> int:
        if value not in {1, 2, 3}:
            msg = "tier must be 1, 2, or 3"
            raise ValueError(msg)
        return value

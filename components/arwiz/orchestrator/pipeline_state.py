from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PipelineStep:
    name: str
    status: str
    duration_ms: float = 0.0
    error: str | None = None


@dataclass
class PipelineState:
    pipeline_type: str
    steps: list[PipelineStep] = field(default_factory=list)
    current_step: int = 0

    def advance(self, step_name: str) -> None:
        self.steps.append(PipelineStep(name=step_name, status="running"))
        self.current_step = len(self.steps) - 1

    def complete_step(self, duration_ms: float) -> None:
        if not self.steps:
            msg = "No active pipeline step to complete"
            raise RuntimeError(msg)
        step = self.steps[self.current_step]
        step.status = "completed"
        step.duration_ms = duration_ms

    def fail_step(self, error: str) -> None:
        if not self.steps:
            msg = "No active pipeline step to fail"
            raise RuntimeError(msg)
        step = self.steps[self.current_step]
        step.status = "failed"
        step.error = error

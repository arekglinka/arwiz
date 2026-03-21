from typing import Protocol

from ..foundation import ArwizConfig, BranchCoverage, OptimizationResult


class OrchestratorProtocol(Protocol):
    def run_profile_optimize_pipeline(
        self,
        script_path: str,
        function_name: str,
        strategy: str = "auto",
        config: ArwizConfig | None = None,
    ) -> OptimizationResult: ...

    def run_coverage_replay_pipeline(
        self,
        script_path: str,
        config: ArwizConfig | None = None,
    ) -> BranchCoverage: ...

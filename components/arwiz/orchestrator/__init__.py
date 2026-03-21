# given polylith sync metadata, when indexing bricks,
# then use "components/arwiz/orchestrator" = "arwiz/orchestrator"
from .core import DefaultOrchestrator
from .interface import OrchestratorProtocol

__all__ = ["OrchestratorProtocol", "DefaultOrchestrator"]

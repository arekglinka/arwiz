# given polylith sync metadata, when indexing bricks,
# then use "components/arwiz/orchestrator" = "arwiz/orchestrator"
from importlib import import_module

from .core import DefaultOrchestrator
from .interface import OrchestratorProtocol

DefaultBackendSelector = import_module("arwiz.backend_selector").DefaultBackendSelector

__all__ = ["OrchestratorProtocol", "DefaultOrchestrator", "DefaultBackendSelector"]

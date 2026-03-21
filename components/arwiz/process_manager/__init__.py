"""Process Manager component - subprocess execution with limits."""

from arwiz.process_manager.core import DefaultProcessManager, ProcessResult
from arwiz.process_manager.interface import ProcessManagerProtocol

__all__ = ["ProcessManagerProtocol", "DefaultProcessManager", "ProcessResult"]

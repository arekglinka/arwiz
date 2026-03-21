"""Coverage Tracer component - AST + runtime branch coverage analysis."""

from arwiz.coverage_tracer.core import DefaultCoverageTracer
from arwiz.coverage_tracer.interface import CoverageTracerProtocol

__all__ = ["CoverageTracerProtocol", "DefaultCoverageTracer"]

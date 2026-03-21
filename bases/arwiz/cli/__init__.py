"""Arwiz CLI - Click-based command-line interface for profiling and optimization."""

import click
from arwiz.cli.commands import coverage, optimize, profile, report


@click.group("arwiz")
@click.version_option(package_name="arwiz")
def cli() -> None:
    """Arwiz - Python performance profiling and optimization tool."""


cli.add_command(profile)
cli.add_command(optimize)
cli.add_command(coverage)
cli.add_command(report)

__all__ = ["cli", "profile", "optimize", "coverage", "report"]

# NOTE: Add to pyproject.toml [project.scripts]:
# arwiz = "arwiz.cli:cli"
# NOTE: Add to pyproject.toml [tool.polylith.bricks]:
# "bases/arwiz/cli" = "arwiz/cli"

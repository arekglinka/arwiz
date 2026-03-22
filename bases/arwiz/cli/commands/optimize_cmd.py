"""Optimize command - suggest optimizations for a function."""

from pathlib import Path

import click
from arwiz.foundation import OptimizationAttempt, OptimizationResult
from arwiz.orchestrator import DefaultOrchestrator
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()


@click.command("optimize")
@click.argument("script", type=click.Path(exists=True))
@click.option("--function", "func_name", required=True, help="Target function name")
@click.option(
    "--strategy",
    type=click.Choice(["auto", "llm", "template"]),
    default="auto",
    help="Optimization strategy",
)
def optimize(script: str, func_name: str, strategy: str) -> None:
    """Suggest optimizations for a specific function."""
    script_path = Path(script)

    with console.status("Running profile + optimize pipeline..."):
        orch = DefaultOrchestrator()
        result = orch.run_profile_optimize_pipeline(
            script_path=str(script_path),
            function_name=func_name,
            strategy=strategy,
        )

    _display_optimizations(result)


def _display_optimizations(result: OptimizationResult) -> None:
    attempts: list[OptimizationAttempt] = result.attempts
    if not attempts:
        console.print("[yellow]No optimizations generated.[/yellow]")
        return

    console.print(
        f"\n[bold]Optimization suggestions for '{result.function_name}':[/bold]"
        f" [dim]({result.file_path})[/dim]\n"
    )
    for i, attempt in enumerate(attempts, 1):
        status = "[green]Valid[/green]" if attempt.syntax_valid else "[red]Invalid[/red]"
        console.print(f"  [bold]#{i}[/bold] ({attempt.strategy}) - {status}")
        if attempt.template_name:
            console.print(f"    Template: {attempt.template_name}")
        console.print(f"    Equivalence: {attempt.passed_equivalence}")
        if attempt.error_message:
            console.print(f"    Error: {attempt.error_message}")
        if attempt.syntax_valid:
            console.print("")
            syntax = Syntax(
                attempt.optimized_code,
                "python",
                theme="monokai",
                line_numbers=True,
            )
            console.print(Panel(syntax, title=f"Optimized ({attempt.strategy})"))
        console.print("")

    if result.best_attempt:
        console.print(
            f"[bold green]Best attempt:[/bold green] {result.best_attempt.attempt_id} "
            f"({result.best_attempt.strategy})"
        )
    else:
        console.print("[yellow]No equivalent optimization found.[/yellow]")
    console.print(f"[bold]Applied:[/bold] {result.applied}")

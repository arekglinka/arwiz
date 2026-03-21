"""Coverage command - trace branch coverage of a target script."""

from pathlib import Path

import click
from arwiz.coverage_tracer import DefaultCoverageTracer
from arwiz.foundation import BranchCoverage
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


@click.command("coverage")
@click.argument("script", type=click.Path(exists=True))
@click.option("--args", default="", help="Space-separated arguments for the script")
@click.option(
    "--store-inputs",
    is_flag=True,
    default=False,
    help="Store input snapshots for uncovered branches",
)
def coverage(script: str, args: str, store_inputs: bool) -> None:
    """Trace branch coverage of a Python script."""
    script_path = Path(script)
    script_args = args.split() if args else []

    tracer = DefaultCoverageTracer()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Tracing branch coverage...", total=None)
        branch_coverage = tracer.trace_branches(script_path, args=script_args)

    _display_coverage(branch_coverage, store_inputs)


def _display_coverage(
    cov: BranchCoverage,
    store_inputs: bool,
) -> None:
    pct_color = (
        "green"
        if cov.coverage_percent >= 80
        else ("yellow" if cov.coverage_percent >= 50 else "red")
    )

    console.print("\n[bold]Branch Coverage Report[/bold]")
    console.print(f"  Script: {cov.script_path}")
    console.print(
        f"  Coverage: [{pct_color}]{cov.coverage_percent:.1f}%[/{pct_color}]"
        f" ({cov.covered_branches}/{cov.total_branches})"
    )
    console.print(f"  Duration: {cov.duration_ms:.2f}ms")

    if cov.uncovered_lines:
        console.print(f"\n  [yellow]Uncovered lines:[/yellow] {cov.uncovered_lines}")

    if store_inputs and cov.uncovered_lines:
        console.print(
            "\n[yellow]Input storage requested — "
            "configure input_storage_path in arwiz config.[/yellow]"
        )

    if cov.branch_details:
        console.print("\n  [bold]Branch details:[/bold]")
        for detail in cov.branch_details[:20]:
            status = "[green]✓[/green]" if detail.taken else "[red]✗[/red]"
            console.print(
                f"    {status} Line {detail.line_number}: {detail.branch_type} ({detail.condition})"
            )

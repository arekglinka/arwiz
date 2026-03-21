"""Optimize command - suggest optimizations for a function."""

from pathlib import Path

import click
from arwiz.foundation import HotSpot, OptimizationAttempt
from arwiz.hotspot import DefaultHotspotDetector
from arwiz.llm_optimizer import DefaultLLMOptimizer
from arwiz.profiler import DefaultProfiler
from arwiz.template_optimizer import DefaultTemplateOptimizer
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

    with console.status("Profiling script..."):
        profiler = DefaultProfiler()
        profile_result = profiler.profile_script(script_path)
        hotspot_detector = DefaultHotspotDetector()
        hotspots = hotspot_detector.detect_hotspots(profile_result)

    target_hotspot = _find_hotspot(hotspots, func_name, script_path)
    if not target_hotspot:
        console.print(f"[yellow]Function '{func_name}' not found in hotspots.[/yellow]")
        return

    source = script_path.read_text()
    attempts: list[OptimizationAttempt] = []

    if strategy in ("auto", "template"):
        tmpl_optimizer = DefaultTemplateOptimizer()
        templates = tmpl_optimizer.detect_applicable_templates(source, target_hotspot)
        for tmpl in templates:
            optimized = tmpl_optimizer.apply_template(source, tmpl)
            attempts.append(
                OptimizationAttempt(
                    attempt_id=f"tmpl_{tmpl}",
                    original_code=source,
                    optimized_code=optimized,
                    strategy="template",
                    template_name=tmpl,
                    syntax_valid=True,
                )
            )

    if strategy in ("auto", "llm"):
        llm_optimizer = DefaultLLMOptimizer()
        attempt = llm_optimizer.optimize_function(source, target_hotspot)
        attempts.append(attempt)

    _display_optimizations(attempts, func_name)


def _find_hotspot(
    hotspots: list[HotSpot],
    func_name: str,
    script_path: Path,
) -> HotSpot | None:
    for h in hotspots:
        if h.function_name == func_name:
            return h
    return None


def _display_optimizations(
    attempts: list[OptimizationAttempt],
    func_name: str,
) -> None:
    if not attempts:
        console.print("[yellow]No optimizations generated.[/yellow]")
        return

    console.print(f"\n[bold]Optimization suggestions for '{func_name}':[/bold]\n")
    for i, attempt in enumerate(attempts, 1):
        status = "[green]Valid[/green]" if attempt.syntax_valid else "[red]Invalid[/red]"
        console.print(f"  [bold]#{i}[/bold] ({attempt.strategy}) - {status}")
        if attempt.template_name:
            console.print(f"    Template: {attempt.template_name}")
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

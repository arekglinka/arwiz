"""Profile command - run profiler on a target script."""

import json
from pathlib import Path

import click
from arwiz.foundation import ProfileResult
from arwiz.hotspot import DefaultHotspotDetector
from arwiz.profiler import DefaultProfiler
from rich.console import Console

console = Console()


@click.command("profile")
@click.argument("script", type=click.Path(exists=True))
@click.option("--args", default="", help="Space-separated arguments for the script")
@click.option("--output", "-o", default=None, help="Output file path for results")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
def profile(script: str, args: str, output: str | None, fmt: str) -> None:
    """Profile a Python script and identify hotspots."""
    script_path = Path(script)
    script_args = args.split() if args else []

    profiler = DefaultProfiler()
    hotspot_detector = DefaultHotspotDetector()

    with console.status(f"Profiling [bold]{script_path}[/bold]..."):
        profile_result = profiler.profile_script(script_path, args=script_args)
        hotspots = hotspot_detector.detect_hotspots(profile_result)

    _display_profile_results(profile_result, hotspots, fmt, output)


def _display_profile_results(
    result: ProfileResult,
    hotspots: list,
    fmt: str,
    output: str | None,
) -> None:
    if fmt == "json":
        data = {
            "profile_id": result.profile_id,
            "script_path": result.script_path,
            "duration_ms": result.duration_ms,
            "hotspot_count": len(hotspots),
            "hotspots": [h.model_dump() for h in hotspots],
        }
        text = json.dumps(data, indent=2)
    else:
        text = _format_profile_text(result, hotspots)

    console.print(text)

    if output:
        Path(output).write_text(text)


def _format_profile_text(
    result: ProfileResult,
    hotspots: list,
) -> str:
    lines = [
        f"[bold]Profile:[/bold] {result.profile_id}",
        f"[bold]Script:[/bold] {result.script_path}",
        f"[bold]Duration:[/bold] {result.duration_ms:.2f}ms",
        f"[bold]Hotspots:[/bold] {len(hotspots)}",
    ]
    if hotspots:
        lines.append("")
        for h in hotspots[:10]:
            lines.append(
                f"  {h.function_name} ({h.self_time_ms:.2f}ms) @ {h.file_path}:{h.line_range[0]}"
            )
    return "\n".join(lines)

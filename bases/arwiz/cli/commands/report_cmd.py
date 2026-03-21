"""Report command - display profile results from a saved profile."""

import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.command("report")
@click.argument("profile", type=click.Path(exists=True))
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["text", "json", "html"]),
    default="text",
    help="Output format",
)
def report(profile: str, fmt: str) -> None:
    """Display a previously saved profile report."""
    profile_path = Path(profile)

    if not profile_path.exists():
        console.print(f"[red]Profile not found: {profile}[/red]")
        raise SystemExit(1)

    try:
        data = json.loads(profile_path.read_text())
    except json.JSONDecodeError:
        console.print(f"[red]Invalid profile format: {profile}[/red]")
        raise SystemExit(1) from None

    if fmt == "json":
        console.print_json(data=data)
    elif fmt == "html":
        _display_html(data)
    else:
        _display_text_report(data)


def _display_text_report(data: dict) -> None:
    console.print("\n[bold]Profile Report[/bold]")
    console.print(f"  ID: {data.get('profile_id', 'N/A')}")
    console.print(f"  Script: {data.get('script_path', 'N/A')}")
    console.print(f"  Duration: {data.get('duration_ms', 0):.2f}ms")

    hotspots = data.get("hotspots", [])
    if hotspots:
        table = Table(title="Hotspots")
        table.add_column("Function", style="cyan")
        table.add_column("Self Time (ms)", justify="right")
        table.add_column("Calls", justify="right")
        table.add_column("File:Line")

        for h in hotspots[:20]:
            table.add_row(
                h.get("function_name", ""),
                f"{h.get('self_time_ms', 0):.2f}",
                str(h.get("call_count", 0)),
                f"{h.get('file_path', '')}:{h.get('line_range', (0,))[0]}",
            )

        console.print(table)


def _display_html(data: dict) -> None:
    html_parts = [
        "<!DOCTYPE html><html><head><title>Arwiz Profile Report</title>",
        "<style>body{font-family:monospace;padding:2em}table{border-collapse:collapse}"
        "th,td{border:1px solid #ddd;padding:8px;text-align:left}"
        "th{background:#f4f4f4}</style></head><body>",
        f"<h1>Profile: {data.get('profile_id', 'N/A')}</h1>",
        f"<p>Script: {data.get('script_path', 'N/A')}</p>",
        f"<p>Duration: {data.get('duration_ms', 0):.2f}ms</p>",
    ]

    hotspots = data.get("hotspots", [])
    if hotspots:
        html_parts.append(
            "<h2>Hotspots</h2><table><tr>"
            "<th>Function</th><th>Self Time</th>"
            "<th>Calls</th><th>Location</th></tr>"
        )
        for h in hotspots[:20]:
            html_parts.append(
                f"<tr><td>{h.get('function_name', '')}</td>"
                f"<td>{h.get('self_time_ms', 0):.2f}ms</td>"
                f"<td>{h.get('call_count', 0)}</td>"
                f"<td>{h.get('file_path', '')}:{h.get('line_range', (0,))[0]}"
                f"</td></tr>"
            )
        html_parts.append("</table>")

    html_parts.append("</body></html>")
    console.print("\n".join(html_parts))

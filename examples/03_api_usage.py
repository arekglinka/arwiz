# Programmatic usage of arwiz as a Python library
#
# Shows how to use arwiz components directly, plus an HTTP client example.
#
# Prerequisites:
#   uv sync                   (install dependencies)
#   uvicorn arwiz.api:app     (start the API server, for the HTTP section)

from pathlib import Path

SCRIPT = Path(__file__).parent / "01_quickstart.py"


def demo_profiler() -> None:
    from arwiz.profiler import DefaultProfiler

    profiler = DefaultProfiler()
    result = profiler.profile_script(str(SCRIPT))
    print("=== Profiler ===")
    print(f"  profile_id : {result.profile_id}")
    print(f"  duration_ms: {result.duration_ms}")
    print(f"  call nodes : {len(result.call_nodes)}")
    for node in result.call_nodes[:5]:
        print(f"    {node.function_name} ({node.module}) - {node.self_time_ms:.1f}ms")


def demo_coverage_tracer() -> None:
    from arwiz.coverage_tracer import DefaultCoverageTracer

    tracer = DefaultCoverageTracer()
    coverage = tracer.trace_branches(str(SCRIPT))
    print("\n=== Branch Coverage ===")
    print(f"  total  : {coverage.total_branches}")
    print(f"  covered: {coverage.covered_branches}")
    print(f"  percent: {coverage.coverage_percent:.1f}%")

    uncovered = tracer.get_uncovered_branches(coverage)
    if uncovered:
        print(f"  uncovered ({len(uncovered)}):")
        for path, line in uncovered[:10]:
            print(f"    {path}:{line}")


def demo_orchestrator() -> None:
    from arwiz.orchestrator import DefaultOrchestrator

    orchestrator = DefaultOrchestrator()
    result = orchestrator.run_profile_optimize_pipeline(
        script_path=str(SCRIPT),
        function_name="compute_sum",
        strategy="template",
    )
    print("\n=== Orchestrator ===")
    print(f"  original : {len(result.original_source)} chars")
    if result.optimized_source:
        print(f"  optimized: {len(result.optimized_source)} chars")
    else:
        print("  optimized: (none generated)")


def demo_api_client() -> None:
    import httpx

    base = "http://localhost:8000"
    script_path = str(SCRIPT)

    resp = httpx.get(f"{base}/health", timeout=10)
    body = resp.json()
    print(f"\n=== API Client (health: {body['status']} v{body['version']}) ===")

    resp = httpx.post(f"{base}/profile", json={"script_path": script_path}, timeout=30)
    p = resp.json()
    print(f"  profile_id : {p['profile_id']}  total_calls: {p['total_calls']}")

    resp = httpx.post(
        f"{base}/optimize",
        json={"script_path": script_path, "function_name": "compute_sum"},
        timeout=30,
    )
    o = resp.json()
    print(f"  strategy   : {o['strategy']}  syntax_valid: {o['syntax_valid']}")

    resp = httpx.post(f"{base}/coverage", json={"script_path": script_path}, timeout=30)
    c = resp.json()
    print(f"  coverage   : {c['coverage_percent']:.1f}%")


if __name__ == "__main__":
    for name, fn in [
        ("Profiler", demo_profiler),
        ("Coverage", demo_coverage_tracer),
        ("Orchestrator", demo_orchestrator),
        ("API client", demo_api_client),
    ]:
        try:
            fn()
        except Exception as exc:
            print(f"{name} demo failed: {exc}")

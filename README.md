# arwiz

AI-assisted Python profiler and optimizer. Profile scripts, detect hotspots, and generate optimization suggestions via templates or LLM providers.

## Features

- Profile Python scripts with `cProfile` subprocess isolation
- Automatic hotspot detection ranked by self-time (filters out import noise)
- Template-based optimizations (vectorize loops, Numba JIT, LRU cache, batch I/O)
- LLM-powered optimization via OpenAI, Anthropic, or Ollama (graceful error handling)
- Hot-reload optimized functions into running modules
- Branch coverage tracing with uncovered-line reporting (including `match/case`)
- Equivalence checking with relative + absolute tolerance and circular reference detection
- Runtime decorator injection (sync and async functions)
- Three interfaces: CLI, Streamlit UI, FastAPI

## Installation

```bash
uv sync
```

## Quick Start

Profile a script and see where time goes:

```bash
$ arwiz profile my_script.py --format json -o results.json
```

Optimize a specific function using template rules:

```bash
$ arwiz optimize my_script.py --function heavy_loop --strategy template
```

Trace branch coverage:

```bash
$ arwiz coverage my_script.py --store-inputs
```

## Examples

The `examples/` directory contains runnable demo scripts:

| File | Description |
|------|-------------|
| `examples/01_quickstart.py` | Simple loop -- good starting point for profiling and template optimization |
| `examples/02_real_world.py` | Pandas data processing with slow `iterrows` and `apply` patterns |
| `examples/03_api_usage.py` | Programmatic API usage and FastAPI client example |
| `examples/api_curl.sh` | curl examples for all 4 API endpoints |

Try the quickstart:

```bash
# Profile the example script
$ arwiz profile examples/01_quickstart.py

# Optimize the compute_sum function using templates
$ arwiz optimize examples/01_quickstart.py --function compute_sum --strategy template

# Trace branch coverage
$ arwiz coverage examples/01_quickstart.py
```

### Using as a Python library

```python
from arwiz.orchestrator import DefaultOrchestrator

orch = DefaultOrchestrator()
result = orch.run_profile_optimize_pipeline(
    script_path="my_script.py",
    function_name="slow_function",
    strategy="auto",
)
if result.best_attempt:
    print(result.best_attempt.optimized_code)
```

### REST API

Start the server, then hit the endpoints:

```bash
$ uvicorn arwiz.api:app --reload
```

```bash
# Health check
$ curl http://localhost:8000/health

# Profile a script
$ curl -X POST http://localhost:8000/profile \
    -H "Content-Type: application/json" \
    -d '{"script_path": "examples/01_quickstart.py"}'

# Optimize a function
$ curl -X POST http://localhost:8000/optimize \
    -H "Content-Type: application/json" \
    -d '{"script_path": "examples/01_quickstart.py", "function_name": "compute_sum", "strategy": "template"}'

# Trace coverage
$ curl -X POST http://localhost:8000/coverage \
    -H "Content-Type: application/json" \
    -d '{"script_path": "examples/01_quickstart.py"}'
```

## Configuration

arwiz looks for configuration in this order (later overrides earlier):

1. Built-in defaults (50% speedup threshold, auto-detect RAM)
2. `.arwiz/config.toml` in the project directory
3. Environment variables prefixed with `ARWIZ_`

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ARWIZ_TIMEOUT` | `300` | Script execution timeout in seconds |
| `ARWIZ_MEMORY_LIMIT` | `auto` | Memory limit in MB (`auto` = 50% of RAM) |
| `ARWIZ_SPEEDUP_THRESHOLD` | `50` | Minimum speedup % to accept (0-100) |
| `ARWIZ_LLM_PROVIDER` | `openai` | LLM provider: `openai`, `anthropic`, `ollama` |
| `ARWIZ_LLM_MODEL` | `gpt-4o` | Model name for the selected provider |
| `ARWIZ_LLM_API_KEY` | -- | API key for the LLM provider |
| `ARWIZ_LLM_BASE_URL` | -- | Custom base URL (useful for self-hosted models) |

### Example config file

```toml
# .arwiz/config.toml
timeout_seconds = 60
memory_limit_mb = 4096
speedup_threshold_percent = 25.0

[llm]
provider = "ollama"
model = "llama3"
base_url = "http://localhost:11434/v1"
```

## Testing

### Run all tests

```bash
$ uv run pytest
```

### Run specific test layers

```bash
# Foundation types only (Pydantic model tests)
$ uv run pytest test/foundation/

# Component tests only (excluding slow profiler)
$ uv run pytest test/components/ --ignore=test/components/test_profiler.py

# Integration tests only
$ uv run pytest test/integration/

# Architecture validation (PEP 420, dependency checks)
$ uv run pytest test/test_architecture.py
```

### Run by marker

```bash
# Skip slow tests (profiler uses real subprocess)
$ uv run pytest -m "not slow"

# Only integration tests
$ uv run pytest -m integration

# Only unit tests
$ uv run pytest -m unit
```

### Lint and format

```bash
$ uv run ruff check .
$ uv run ruff format --check .
$ uv run ruff format .  # auto-fix formatting
```

### Coverage report

```bash
$ uv run pytest --cov=arwiz --cov-report=term-missing
```

### Test structure

| Directory | What it covers |
|-----------|---------------|
| `test/foundation/types/` | Pydantic model tests (ProfileResult, HotSpot, OptimizationAttempt, etc.) |
| `test/fixtures/` | Target scripts for profiling and fixture validation |
| `test/components/` | Per-component unit tests (13 components) |
| `test/bases/` | Entry point tests (CLI, Streamlit, FastAPI) |
| `test/integration/` | End-to-end pipeline tests |
| `test/test_architecture.py` | AST-based architecture validation |

350 tests across 25 test files.

### Things to know

- Profiler tests are slow (~30s) because they profile real scripts in a subprocess. Use `-m "not slow"` to skip them.
- CLI integration tests (`test/integration/test_cli_workflow.py`) run the real CLI and are also marked `@pytest.mark.slow`.
- FastAPI tests use `TestClient` with no server startup needed.
- Streamlit tests verify imports only, not browser rendering.
- LSP errors from pyrefly are false positives — it can't resolve Polylith namespace packages at static analysis time, but runtime imports work correctly.

## Entry Points

**CLI** (default):

```bash
$ arwiz profile <script>
$ arwiz optimize <script> --function <name>
$ arwiz coverage <script>
$ arwiz report <script>
```

**Streamlit UI**:

```bash
$ streamlit run -m arwiz.streamlit_ui.app
```

**FastAPI server**:

```bash
$ uvicorn arwiz.api:app --reload
```

## Architecture

Built as a Polylith workspace with 16 bricks (13 components, 3 bases). Uses PEP 420 implicit namespace packages, so there are no `__init__.py` files at the namespace level.

## Project Structure

```
arwiz/
  components/arwiz/        # 13 components
    config/                # Configuration models
    coverage_tracer/       # Branch coverage tracing
    decorator_injector/    # Runtime decorator injection
    equivalence/           # Optimized code equivalence checking
    foundation/            # Core types (ProfileResult, HotSpot, etc.)
    hot_reload/            # Hot-reload support
    hotspot/               # Hotspot detection and ranking
    input_manager/         # Input capture and replay
    llm_optimizer/         # LLM-based optimization
    orchestrator/          # Profile-then-optimize pipeline
    process_manager/       # Subprocess management
    profiler/              # cProfile-based profiling
    template_optimizer/    # AST-based template optimizations
  bases/arwiz/             # 3 entry points
    cli/                   # Click-based CLI
    streamlit_ui/          # Streamlit dashboard
    api/                   # FastAPI REST API
  test/                    # 350 tests
    foundation/types/      # Model validation tests
    fixtures/              # Target scripts and fixtures
    components/            # Component unit tests
    bases/                 # Entry point tests
    integration/           # End-to-end tests
    test_architecture.py   # Architecture validation
  examples/                # Runnable demo scripts
    01_quickstart.py       # Simple loop profiling demo
    02_real_world.py       # Pandas data processing demo
    03_api_usage.py        # Programmatic API usage
    api_curl.sh            # curl examples for REST API
```

# arwiz

AI-assisted Python profiler and optimizer. Profile scripts, detect hotspots, and generate optimization suggestions via templates or LLM providers.

## Features

- Profile Python scripts with `cProfile` subprocess isolation
- Automatic hotspot detection ranked by self-time
- Template-based optimizations (vectorize loops, Numba JIT, LRU cache, batch I/O)
- LLM-powered optimization via OpenAI, Anthropic, or Ollama
- Branch coverage tracing with uncovered-line reporting
- Equivalence checking to validate optimized code correctness
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

286 tests across 24 test files.

### Things to know

- Profiler tests are slow (~30s) because they profile real scripts in a subprocess. Use `-m "not slow"` to skip them.
- CLI smoke tests use real subprocess invocation of the `arwiz` CLI.
- FastAPI tests use `TestClient` with no server startup needed.
- Streamlit tests verify imports only, not browser rendering.

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
  test/                    # 286 tests
    foundation/types/      # Model validation tests
    fixtures/              # Target scripts and fixtures
    components/            # Component unit tests
    bases/                 # Entry point tests
    integration/           # End-to-end tests
    test_architecture.py   # Architecture validation
```

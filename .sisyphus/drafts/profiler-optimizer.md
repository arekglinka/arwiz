# Draft: Python Profiler/Debugger/Optimizer Tool

## Requirements (confirmed)

### Core Objective
Create a tool that takes a Python project location (virtualenv + working directory) + script + CLI args, then:
1. Profile the script execution
2. Identify bottlenecks
3. Debug and stop at bottleneck functions
4. Write optimized versions dynamically
5. Test optimizations iteratively without full reruns

### Target Architecture Pattern
- Follow trading-bot Polylith structure
- Namespace: TBD (e.g., `hotspot_optimizer`, `py_optimizer`)
- Components for modularity
- Bases for CLI/GUI entry points

## Mode 1: Profiling + Optimization Loop

**Workflow**:
1. Run script with profiler (cProfile/py-spy)
2. Parse results → identify hotspots
3. Run with debugger, break at bottleneck functions
4. Write optimized version (try numpy → numba → cython → polars → rust)
5. Hot-reload optimized version
6. Test on samples, then full inputs
7. Monitor memory to avoid OOM

**Open Questions**:
- How to handle functions with side effects?
- What constitutes "significant speedup" threshold?
- How to preserve semantic equivalence?

## Mode 2: Input Coverage Mode

**Workflow**:
1. Analyze computation graph of original script
2. Prepare inputs that cover all branches
3. Store inputs in gitignored directory
4. Add decorators to original code for input override
5. Enable fast iteration testing

**Open Questions**:
- How to trace computation graph? (AST, dynamic tracing, etc.)
- What decorator pattern to use?
- How to handle non-deterministic code?

## Technical Decisions (CONFIRMED)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Namespace** | `arwiz` | User selected |
| **Entry Point** | Click CLI + Streamlit + FastAPI endpoint | Multi-modal access |
| **Hot-reload modes** | ALL 3: function args/returns, full replacement, variable injection | Maximum flexibility |
| **Coverage tracing** | AST-based static analysis + Runtime tracing | Hybrid approach |
| Profiler | cProfile, py-spy, line_profiler | cProfile is stdlib, py-spy is production-safe |
| Debugger | pdb, debugpy, custom | Need programmatic control |
| Optimization order | numpy → numba → cython → polars → rust | As specified by user |
| Memory monitoring | psutil, memory_profiler, resource | Need OOM prevention |

## Test Strategy
- **Approach**: TDD (Test-Driven Development)
- **Framework**: pytest with pytest-cov
- **Structure**: `test/` directory mirroring trading-bot pattern
- **Markers**: unit, integration, slow, benchmark

## Quality Thresholds
- **Speedup threshold**: 50% (only accept optimizations that give >50% improvement)
- **Memory limits**: Auto-detect system RAM + configurable limits
- **Semantic equivalence**: Test optimized version against original on same inputs

## Decorator Injection Strategy
- **AST transformation**: Parse target script AST, inject decorators at call sites
- **Import hooks**: `sys.meta_path` to wrap functions at import time  
- **Source rewriting**: Write decorated copy to temp location
- User can choose which approach based on their use case

## Visualization (Streamlit + FastAPI)
- **Profiling results**: Flame graphs, call trees, timeline
- **Optimization history**: Track speedup attempts and results
- **Live streaming**: Real-time profiling with live-updating charts
- **Code comparison**: Side-by-side diff of original vs optimized

## Data Storage
- **Captured inputs**: `.arwiz/inputs/` (gitignored)
- **Optimization cache**: `.arwiz/cache/`
- **Profiling results**: `.arwiz/profiles/`

## Rust Strategy
- **Start**: Pure Python implementation
- **Later**: Add Rust components via maturin/PyO3 if profiling shows need
- **Candidates**: Hot-reload mechanism, AST parsing, profiling aggregation

## Scope Boundaries

### INCLUDE (v0.1):
- Click CLI interface for launching scripts
- Streamlit UI + FastAPI endpoint for visualization
- Profiling integration (cProfile, py-spy, line_profiler)
- **AI-assisted optimization** via LLM code generation (OpenAI/Anthropic/local)
- Optimization templates as fallback (numpy vectorization, numba JIT, caching)
- Hot-reload mechanism (3 modes: args/returns, full replacement, variable injection)
- Input sampling system with coverage mode
- Memory monitoring with auto-detect + configurable limits
- Decorator-based input override (AST + runtime tracing)
- Code validation before hot-reload
- Rollback mechanism on failure

### AI Generation Guardrails:
- LLM generates optimization candidates
- **Always validate**: syntax check, type check, semantic equivalence test
- **User approval**: show diff before applying
- **Rollback**: auto-revert to original on failure
- **Fallback**: template-based if LLM fails

### EXCLUDE (for now):
- Distributed execution
- Cloud deployment
- Multi-language support (Python only)
- Remote debugging over network
- Rust components (v0.2+)
- Async/threading target support (document limitation)

## Research Findings

### From trading-bot structure:
- Polylith with loose theme
- PEP 420 namespaces (no __init__.py in ns dirs)
- `[tool.polylith.bricks]` for component registration
- `[tool.hatch.build].dev-mode-dirs` for dev mode
- Rust components via maturin + PyO3

### From polylith-check skill:
- Maturin pattern with try/except fallback
- Rust component structure: `core.py`, `interface.py`, `rust/`

### From performance-profiling skill:
- cProfile for func-level hotspots
- line_profiler for line-by-line
- py-spy for realtime visualization
- Optimization patterns (vectorization, caching, boolean masks)

# arwiz: Python Profiler/Debugger/Optimizer Tool

## TL;DR

> **Quick Summary**: Build a Python profiling/debugging/optimization tool with AI-assisted code generation using Polylith architecture. Profile scripts → identify bottlenecks → generate optimizations via LLM → hot-reload and test.
> 
> **Deliverables**:
> - Click CLI (`arwiz profile|optimize|coverage|report`)
> - Streamlit UI with flame graphs, call trees, code comparison
> - FastAPI endpoint for programmatic access
> - AI-assisted optimization with LLM code generation
> - Hot-reload mechanism with 3 injection modes
> - Coverage mode with branch tracing and input capture
> 
> **Estimated Effort**: XL
> **Parallel Execution**: YES - 4 waves
> **Critical Path**: Foundation → Components → Entry Points → Integration

---

## Context

### Original Request
Create a project matching trading-bot's Polylith structure that:
1. Takes a Python project location (virtualenv, working directory) + script + CLI args
2. Profiles execution, identifies bottlenecks, runs debugger at bottlenecks
3. Writes optimized versions dynamically (numpy → numba → cython → polars → rust)
4. Hot-reloads optimized versions without full script reruns
5. Tests on samples, monitors memory to prevent OOM
6. Coverage mode: prepare inputs covering all computation graph branches

### Interview Summary
**Key Discussions**:
- Namespace: `arwiz`
- Entry points: Click CLI + Streamlit UI + FastAPI endpoint (all v0.1)
- Optimization: AI-assisted via LLM (OpenAI/Anthropic/local) + template fallback
- Hot-reload: 3 modes (args/returns, full replacement, variable injection)
- Coverage: AST static analysis + runtime tracing
- Speedup threshold: 50% (only accept optimizations with >50% improvement)
- Memory: Auto-detect + configurable limits
- Testing: TDD with pytest

**Research Findings**:
- trading-bot uses Polylith "loose" theme with PEP 420 namespaces
- Component pattern: `__init__.py` + `interface.py` + `core.py`
- Foundation has zero external dependencies
- Architecture validation tests via AST analysis
- Test structure: flat `test/` at workspace root

### Metis Review
**Identified Gaps** (addressed):
- **Who writes optimized code?**: AI-assisted with LLM generation + template fallback
- **Subprocess vs in-process**: Subprocess (safer isolation)
- **Optimization chain**: Decision tree based on bottleneck type, not linear
- **Debugger**: Omit from v0.1, focus on profiling/optimization
- **Async/threading**: Exclude from v0.1, document as limitation
- **Target Python versions**: 3.9-3.13 with version-specific AST handling

---

## Work Objectives

### Core Objective
Build a complete Python profiling/optimization tool with AI-assisted code generation, visual UI, and programmatic API.

### Concrete Deliverables
- `workspace.toml` with `namespace = "arwiz"`, `theme = "loose"`
- `pyproject.toml` with uv workspace, hatchling, ruff, pytest, pyrefly configs
- 10 reusable components following Polylith pattern
- 1 CLI base for Click commands
- Streamlit UI with visualization
- FastAPI endpoint for API access
- Architecture validation tests
- TDD test suite with >80% coverage

### Definition of Done
- [ ] `uv run arwiz profile <script>` produces profiling results
- [ ] `uv run arwiz optimize <script> --function <name>` generates and applies optimization
- [ ] `uv run arwiz coverage <script>` captures branch-covering inputs
- [ ] Streamlit UI displays flame graphs and code diffs
- [ ] FastAPI `/profile` and `/optimize` endpoints work
- [ ] All tests pass: `uv run pytest`
- [ ] Architecture validated: `uv run pytest test/test_architecture.py`

### Must Have
- Subprocess execution with timeout/memory limits
- AI-assisted optimization with user approval before apply
- Semantic equivalence check before hot-reload
- Rollback mechanism on optimization failure
- Never modify user's original source files

### Must NOT Have (Guardrails)
- NO in-process target execution (always subprocess)
- NO auto-apply optimizations without user approval
- NO modification of user's original source files
- NO support for async/threading targets in v0.1
- NO Rust components in v0.1
- NO external dependencies in foundation component

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed.

### Test Decision
- **Infrastructure exists**: NO (will create)
- **Automated tests**: TDD (RED-GREEN-REFACTOR for each component)
- **Framework**: pytest + pytest-cov + pytest-benchmark
- **TDD workflow**: Each task follows RED (failing test) → GREEN (minimal impl) → REFACTOR

### QA Policy
Every task includes agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **CLI**: Bash (run commands, check exit codes, validate output)
- **Streamlit**: Playwright (navigate, interact, screenshot)
- **FastAPI**: curl (send requests, assert responses)
- **Library/Module**: Bash (python -c "import arwiz; ...")

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — foundation + scaffolding):
├── Task 1: Project scaffolding (workspace.toml, pyproject.toml, .gitignore) [quick]
├── Task 2: Foundation types (ProfileResult, HotSpot, OptimizationResult, etc.) [quick]
├── Task 3: Architecture validation test [quick]
├── Task 4: Test fixtures (sample target scripts) [quick]
├── Task 5: Process manager component [quick]
└── Task 6: Configuration component [quick]

Wave 2 (After Wave 1 — core components, MAX PARALLEL):
├── Task 7: Profiler component (cProfile + line_profiler wrapper) [deep]
├── Task 8: Hotspot detector component [quick]
├── Task 9: Equivalence checker component [quick]
├── Task 10: Input manager component [quick]
├── Task 11: Coverage tracer component (sys.settrace) [unspecified-high]
├── Task 12: Decorator injector component (AST rewrite) [unspecified-high]
├── Task 13: Hot-reload component (sys.modules manipulation) [unspecified-high]
├── Task 14: LLM optimizer component (OpenAI/Anthropic integration) [deep]
└── Task 15: Template optimizer component (numpy, numba patterns) [quick]

Wave 3 (After Wave 2 — entry points):
├── Task 16: CLI base (Click commands: profile, optimize, coverage, report) [quick]
├── Task 17: Streamlit UI base [visual-engineering]
├── Task 18: FastAPI endpoint base [quick]
└── Task 19: Orchestrator component (pipeline coordination) [deep]

Wave 4 (After Wave 3 — integration):
├── Task 20: Profile → Optimize pipeline integration [unspecified-high]
├── Task 21: Coverage → Replay pipeline integration [unspecified-high]
└── Task 22: End-to-end smoke tests [unspecified-high]

Wave FINAL (After ALL tasks — 4 parallel reviews, then user okay):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
└── Task F4: Scope fidelity check (deep)
-> Present results -> Get explicit user okay

Critical Path: T1 → T2 → T7 → T14 → T16 → T19 → T20 → F1-F4 → user okay
Parallel Speedup: ~65% faster than sequential
Max Concurrent: 9 (Wave 2)
```

### Dependency Matrix

| Tasks | Depends On | Blocks |
|-------|------------|--------|
| 1-6 | — | 7-15, 16-19 |
| 7 | 2, 5 | 16, 19, 20 |
| 8 | 2 | 14, 16, 19 |
| 9 | 2 | 14, 19, 20 |
| 10 | 2 | 11, 12, 19 |
| 11 | 2, 10 | 16, 19, 21 |
| 12 | 2, 10 | 16, 19, 21 |
| 13 | 2 | 14, 19, 20 |
| 14 | 2, 8, 9, 13 | 16, 19, 20 |
| 15 | 2, 9 | 14, 19 |
| 16 | 7, 8, 11, 14 | 19, 20 |
| 17 | 7, 8, 14 | 22 |
| 18 | 7, 8, 14 | 22 |
| 19 | 7-16 | 20, 21, 22 |
| 20 | 7-14, 16, 19 | F1-F4 |
| 21 | 10-12, 16, 19 | F1-F4 |
| 22 | 16-19 | F1-F4 |
| F1-F4 | 20-22 | user okay |

### Agent Dispatch Summary

- **Wave 1**: **6** — T1-T4 → `quick`, T5-T6 → `quick`
- **Wave 2**: **9** — T7, T14, T19 → `deep`, T8, T9, T10, T15 → `quick`, T11-T13 → `unspecified-high`
- **Wave 3**: **4** — T16, T18 → `quick`, T17 → `visual-engineering`, T19 → `deep`
- **Wave 4**: **3** — T20-T22 → `unspecified-high`
- **FINAL**: **4** — F1 → `oracle`, F2-F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

> Implementation + Test = ONE Task. Never separate.
> EVERY task has: Recommended Agent Profile + Parallelization + QA Scenarios.

---

### Wave 1: Foundation + Scaffolding

- [x] 1. Project Scaffolding + Configuration

  **What to do**:
  - Create `workspace.toml` with `namespace = "arwiz"`, `theme = "loose"`
  - Create `pyproject.toml` with uv workspace, hatchling, all dependencies
  - Create `.gitignore` (Python standard + `.arwiz/`, `.benchmarks/`, `htmlcov/`)
  - Create `.python-version` (3.13)
  - Create `.pre-commit-config.yaml` (ruff, pyrefly, standard checks)
  - Create directory structure: `bases/`, `components/`, `projects/`, `development/`, `test/`, `scripts/`
  - Run `uv sync` to initialize workspace

  **Must NOT do**:
  - Do NOT create any component files yet (just directories)
  - Do NOT add Rust configuration

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Standard project initialization, well-defined structure
  - **Skills**: [`conventional-commits`]
    - `conventional-commits`: For initial commit message formatting

  **Parallelization**:
  - **Can Run In Parallel**: NO (foundation for everything)
  - **Parallel Group**: Wave 1 (sequential start)
  - **Blocks**: All other tasks
  - **Blocked By**: None

  **References**:
  - `~/wsp/trading-bot/workspace.toml` - Polylith workspace config pattern
  - `~/wsp/trading-bot/pyproject.toml` - Dependency and tool config pattern
  - `~/wsp/trading-bot/.gitignore` - Gitignore patterns to copy

  **Acceptance Criteria**:
  - [ ] `uv sync` completes without errors
  - [ ] `uv run python -c "import arwiz"` does NOT raise (namespace exists)
  - [ ] `uv run ruff check .` passes (no files to check yet)
  - [ ] Directory structure matches trading-bot pattern

  **QA Scenarios**:
  ```
  Scenario: Workspace initialization
    Tool: Bash
    Preconditions: Empty project directory
    Steps:
      1. Run `uv sync`
      2. Check exit code is 0
      3. Verify `workspace.toml` contains `namespace = "arwiz"`
      4. Verify `pyproject.toml` contains `[tool.polylith.bricks]`
    Expected Result: All checks pass
    Evidence: .sisyphus/evidence/task-01-init.txt
  ```

  **Commit**: YES
  - Message: `chore(init): initialize arwiz polylith workspace`
  - Files: All created files
  - Pre-commit: None (initial commit)

---

- [x] 2. Foundation Types Component

  **What to do**:
  - Create `components/arwiz/foundation/` directory structure
  - Create `components/arwiz/foundation/__init__.py` (re-exports)
  - Create `components/arwiz/foundation/types/__init__.py`
  - Create `components/arwiz/foundation/types/profile.py` with Pydantic models:
    - `ProfileResult`: profile_id, script_path, duration_ms, call_tree
    - `HotSpot`: function_name, file_path, line_range, cumulative_time, self_time
    - `CallNode`: function_name, children, cumulative_time
  - Create `components/arwiz/foundation/types/optimization.py`:
    - `OptimizationAttempt`: original_code, optimized_code, strategy, llm_model
    - `OptimizationResult`: speedup_percent, passed_equivalence, applied
  - Create `components/arwiz/foundation/types/coverage.py`:
    - `BranchCoverage`: total_branches, covered_branches, uncovered_lines
    - `InputSnapshot`: args, kwargs, timestamp, hash
  - Create `components/arwiz/foundation/types/config.py`:
    - `ArwizConfig`: target_python, memory_limit_mb, timeout_seconds
    - `ProfilingConfig`: profiler_type, line_profiling, warmup_runs
  - Add brick to `[tool.polylith.bricks]` in root pyproject.toml
  - Write TDD tests in `test/foundation/types/`

  **Must NOT do**:
  - Do NOT import any external dependencies (only pydantic, stdlib)
  - Do NOT add business logic (types only)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Pydantic model definitions are straightforward
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T3, T4, T5, T6 after T1)
  - **Parallel Group**: Wave 1
  - **Blocks**: T7-T15 (all components depend on types)
  - **Blocked By**: T1

  **References**:
  - `~/wsp/trading-bot/components/trading_bot/foundation/types/models.py` - Pydantic model patterns
  - `~/wsp/trading-bot/components/trading_bot/foundation/__init__.py` - Re-export pattern

  **Acceptance Criteria**:
  - [ ] All Pydantic models defined with proper type hints
  - [ ] `uv run pyrefly check components/arwiz/foundation/` passes
  - [ ] `uv run pytest test/foundation/ -v` passes
  - [ ] `from arwiz.foundation import ProfileResult` works

  **QA Scenarios**:
  ```
  Scenario: Foundation types importable
    Tool: Bash
    Steps:
      1. Run `uv run python -c "from arwiz.foundation import ProfileResult, HotSpot, OptimizationResult, BranchCoverage, ArwizConfig"`
      2. Check exit code is 0
    Expected Result: All types import without error
    Evidence: .sisyphus/evidence/task-02-foundation-import.txt
  ```

  **Commit**: YES
  - Message: `feat(foundation): add core type definitions`
  - Files: components/arwiz/foundation/**, test/foundation/**

---

- [x] 3. Architecture Validation Test

  **What to do**:
  - Create `test/test_architecture.py` with AST-based validation
  - Validate: foundation has no external dependencies
  - Validate: components only import from interfaces, not cores
  - Validate: dependency direction is bases → components → foundation
  - Validate: no circular dependencies between components
  - Validate: interface complexity limit (max 10 public methods)
  - Write tests that will FAIL initially (foundation doesn't exist yet)

  **Must NOT do**:
  - Do NOT modify existing code to pass tests

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Standard AST analysis, copy pattern from trading-bot
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T2, T4, T5, T6 after T1)
  - **Parallel Group**: Wave 1
  - **Blocks**: T7-T15 (validation during development)
  - **Blocked By**: T1

  **References**:
  - `~/wsp/trading-bot/test/test_architecture.py` - Full implementation to copy/adapt
  - Change `trading_bot` namespace references to `arwiz`

  **Acceptance Criteria**:
  - [ ] `uv run pytest test/test_architecture.py -v` passes (after foundation created)
  - [ ] Validation catches: wrong import direction, foundation external deps, circular deps

  **QA Scenarios**:
  ```
  Scenario: Architecture validation runs
    Tool: Bash
    Steps:
      1. Run `uv run pytest test/test_architecture.py -v`
      2. Check exit code is 0
    Expected Result: All architecture tests pass
    Evidence: .sisyphus/evidence/task-03-arch-validation.txt
  ```

  **Commit**: YES
  - Message: `test(architecture): add AST-based validation tests`
  - Files: test/test_architecture.py

---

- [x] 4. Test Fixtures (Sample Target Scripts)

  **What to do**:
  - Create `test/fixtures/` directory
  - Create `test/fixtures/__init__.py`
  - Create `test/fixtures/conftest.py` with pytest fixtures
  - Create sample target scripts:
    - `test/fixtures/targets/simple_loop.py`: Basic for loop (optimization target)
    - `test/fixtures/targets/nested_calls.py`: Nested function calls (profiling target)
    - `test/fixtures/targets/numpy_heavy.py`: NumPy operations (vectorization target)
    - `test/fixtures/targets/io_bound.py`: File I/O operations (batching target)
    - `test/fixtures/targets/branching.py`: Complex branching (coverage target)
  - Create synthetic data if needed (small parquet files)

  **Must NOT do**:
  - Do NOT use external data files

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple test fixture creation
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T2, T3, T5, T6 after T1)
  - **Parallel Group**: Wave 1
  - **Blocks**: T7-T15 (needed for component tests)
  - **Blocked By**: T1

  **References**:
  - `~/wsp/trading-bot/test/fixtures/` - Fixture structure pattern

  **Acceptance Criteria**:
  - [ ] All target scripts are valid Python (syntax check)
  - [ ] `uv run pytest test/fixtures/test_fixtures.py -v` passes
  - [ ] Each target has a docstring explaining its purpose

  **QA Scenarios**:
  ```
  Scenario: Target scripts runnable
    Tool: Bash
    Steps:
      1. For each target script, run `uv run python test/fixtures/targets/<script>.py`
      2. Check exit code is 0
    Expected Result: All scripts run without error
    Evidence: .sisyphus/evidence/task-04-fixtures.txt
  ```

  **Commit**: YES
  - Message: `test(fixtures): add sample target scripts for testing`
  - Files: test/fixtures/**

---

- [x] 5. Process Manager Component

  **What to do**:
  - Create `components/arwiz/process_manager/` with standard Polylith pattern
  - Create `interface.py` with `ProcessManagerProtocol`:
    - `run_script(script_path, args, timeout, memory_limit) -> ProcessResult`
    - `kill_process(pid) -> None`
    - `get_memory_usage(pid) -> int`
  - Create `core.py` with `DefaultProcessManager`:
    - Use `subprocess.Popen` for subprocess execution
    - Use `psutil` for memory monitoring and process control
    - Use `resource.setrlimit` for memory limits (Unix)
    - Handle timeout with `signal.alarm` or threading
    - Capture stdout/stderr
  - Write TDD tests in `test/components/test_process_manager.py`
  - Add brick to `[tool.polylith.bricks]`

  **Must NOT do**:
  - Do NOT run target scripts in-process
  - Do NOT skip timeout/memory limit implementation

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: subprocess + psutil is well-documented
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T2, T3, T4, T6 after T1)
  - **Parallel Group**: Wave 1
  - **Blocks**: T7 (profiler needs process manager)
  - **Blocked By**: T1, T2

  **References**:
  - Python stdlib `subprocess` documentation
  - `psutil` documentation for process management
  - `resource` module for RLIMIT_AS

  **Acceptance Criteria**:
  - [ ] `uv run pytest test/components/test_process_manager.py -v` passes
  - [ ] Subprocess runs with timeout enforced
  - [ ] Memory limit kills process when exceeded
  - [ ] stdout/stderr captured in ProcessResult

  **QA Scenarios**:
  ```
  Scenario: Process timeout enforced
    Tool: Bash
    Steps:
      1. Run test that launches infinite loop script with 2s timeout
      2. Verify process is killed after timeout
      3. Check ProcessResult.timeout is True
    Expected Result: Process killed, timeout flag set
    Evidence: .sisyphus/evidence/task-05-timeout.txt

  Scenario: Memory limit enforced
    Tool: Bash
    Steps:
      1. Run test that allocates 500MB with 100MB limit
      2. Verify process is OOM-killed
    Expected Result: Process killed on memory exceed
    Evidence: .sisyphus/evidence/task-05-memory-limit.txt
  ```

  **Commit**: YES
  - Message: `feat(process_manager): add subprocess execution with limits`
  - Files: components/arwiz/process_manager/**, test/components/test_process_manager.py

---

- [x] 6. Configuration Component

  **What to do**:
  - Create `components/arwiz/config/` with standard Polylith pattern
  - Create `interface.py` with `ConfigLoaderProtocol`:
    - `load_config(config_path: Path | None) -> ArwizConfig`
    - `get_default_config() -> ArwizConfig`
  - Create `core.py` with `DefaultConfigLoader`:
    - Load from `.arwiz/config.toml` if exists
    - Merge with defaults
    - Environment variable overrides (ARWIZ_*)
    - Auto-detect system memory for default limit
  - Write TDD tests in `test/components/test_config.py`
  - Add brick to `[tool.polylith.bricks]`

  **Must NOT do**:
  - Do NOT hardcode all config values
  - Do NOT require config file (use sensible defaults)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Config loading is straightforward
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T2, T3, T4, T5 after T1)
  - **Parallel Group**: Wave 1
  - **Blocks**: T7-T15 (all components need config)
  - **Blocked By**: T1, T2

  **References**:
  - `tomllib` (stdlib) for TOML parsing
  - `psutil.virtual_memory()` for system memory detection

  **Acceptance Criteria**:
  - [ ] `uv run pytest test/components/test_config.py -v` passes
  - [ ] Default config auto-detects system memory
  - [ ] Config file overrides work
  - [ ] Environment variable overrides work

  **QA Scenarios**:
  ```
  Scenario: Config auto-detects memory
    Tool: Bash
    Steps:
      1. Run `uv run python -c "from arwiz.config import get_default_config; c = get_default_config(); print(c.memory_limit_mb)"`
      2. Verify value is reasonable (50% of system RAM)
    Expected Result: Memory limit is auto-detected
    Evidence: .sisyphus/evidence/task-06-config-memory.txt
  ```

  **Commit**: YES
  - Message: `feat(config): add configuration loading with auto-detection`
  - Files: components/arwiz/config/**, test/components/test_config.py

---

### Wave 2: Core Components

- [x] 7. Profiler Component

  **What to do**:
  - Create `components/arwiz/profiler/` with standard Polylith pattern
  - Create `interface.py` with `ProfilerProtocol`:
    - `profile_script(script_path, args, config) -> ProfileResult`
    - `profile_function(module_path, function_name, args, kwargs) -> ProfileResult`
  - Create `core.py` with `DefaultProfiler`:
    - Wrap `cProfile.Profile` for function-level profiling
    - Integrate `line_profiler.LineProfiler` for line-level
    - Parse profile stats into `ProfileResult` with call tree
    - Support warmup runs to eliminate startup overhead
    - Output: JSON + pstats file
  - Create `parsers.py` for pstats → ProfileResult conversion
  - Write TDD tests in `test/components/test_profiler.py`
  - Add brick to `[tool.polylith.bricks]`

  **Must NOT do**:
  - Do NOT profile in arwiz's own process (use process_manager)
  - Do NOT include py-spy integration in v0.1 (add as CLI convenience later)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: cProfile integration, pstats parsing, call tree building
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T8-T15)
  - **Parallel Group**: Wave 2
  - **Blocks**: T16 (CLI), T17 (Streamlit), T19 (Orchestrator)
  - **Blocked By**: T1, T2, T5

  **References**:
  - Python stdlib `cProfile` and `pstats` documentation
  - `line_profiler` PyPI package
  - `~/wsp/trading-bot/components/trading_bot/strategy_perf/` - Performance profiling patterns

  **Acceptance Criteria**:
  - [ ] `uv run pytest test/components/test_profiler.py -v` passes
  - [ ] Profiling overhead < 10% for functions > 100ms
  - [ ] Call tree correctly represents nested calls
  - [ ] Output is machine-readable JSON

  **QA Scenarios**:
  ```
  Scenario: Profile simple script
    Tool: Bash
    Steps:
      1. Run `uv run python -c "from arwiz.profiler import DefaultProfiler; p = DefaultProfiler(); r = p.profile_script('test/fixtures/targets/simple_loop.py', [], ArwizConfig()); print(r.duration_ms)"`
      2. Verify duration_ms > 0
      3. Verify hotspots list is populated
    Expected Result: ProfileResult with valid data
    Evidence: .sisyphus/evidence/task-07-profile-simple.txt
  ```

  **Commit**: YES
  - Message: `feat(profiler): add cProfile and line_profiler integration`
  - Files: components/arwiz/profiler/**, test/components/test_profiler.py

---

- [x] 8. Hotspot Detector Component

  **What to do**:
  - Create `components/arwiz/hotspot/` with standard Polylith pattern
  - Create `interface.py` with `HotspotDetectorProtocol`:
    - `detect_hotspots(profile_result, threshold_pct) -> list[HotSpot]`
    - `rank_by_impact(hotspots) -> list[HotSpot]` (sorted by potential impact)
  - Create `core.py` with `DefaultHotspotDetector`:
    - Analyze ProfileResult.call_tree
    - Filter by cumulative_time percentage
    - Identify leaf functions (most impact from optimization)
    - Skip C extension functions (can't optimize)
    - Detect optimization opportunities (loop patterns, etc.)
  - Write TDD tests in `test/components/test_hotspot.py`
  - Add brick to `[tool.polylith.bricks]`

  **Must NOT do**:
  - Do NOT include C extension functions in optimization candidates
  - Do NOT suggest optimizations for functions < 5% of total time

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Analysis logic, no external integrations
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T7, T9-T15)
  - **Parallel Group**: Wave 2
  - **Blocks**: T14 (LLM optimizer needs hotspots)
  - **Blocked By**: T1, T2

  **References**:
  - Performance-profiling skill: Bottleneck identification patterns

  **Acceptance Criteria**:
  - [ ] `uv run pytest test/components/test_hotspot.py -v` passes
  - [ ] Hotspots ranked by cumulative time
  - [ ] C extension functions filtered out
  - [ ] Threshold filtering works

  **QA Scenarios**:
  ```
  Scenario: Detect hotspots in nested calls
    Tool: Bash
    Steps:
      1. Profile nested_calls.py fixture
      2. Run hotspot detection with 10% threshold
      3. Verify only functions > 10% time are returned
    Expected Result: Correct hotspot filtering
    Evidence: .sisyphus/evidence/task-08-hotspot-detect.txt
  ```

  **Commit**: YES
  - Message: `feat(hotspot): add bottleneck identification`
  - Files: components/arwiz/hotspot/**, test/components/test_hotspot.py

---

- [x] 9. Equivalence Checker Component

  **What to do**:
  - Create `components/arwiz/equivalence/` with standard Polylith pattern
  - Create `interface.py` with `EquivalenceCheckerProtocol`:
    - `check_equivalence(original_result, optimized_result, tolerance) -> bool`
    - `compare_outputs(original, optimized, config) -> ComparisonResult`
  - Create `core.py` with `DefaultEquivalenceChecker`:
    - Handle primitive types (int, str, bool)
    - Handle collections (list, dict, set)
    - Handle NumPy arrays with `np.allclose()`
    - Handle NaN/inf comparisons
    - Handle floating-point tolerance (default 1e-6)
    - Handle non-serializable types (mark as incomparable)
  - Create `tolerance.py` for tolerance calculations
  - Write TDD tests in `test/components/test_equivalence.py`
  - Add brick to `[tool.polylith.bricks]`

  **Must NOT do**:
  - Do NOT fail on non-serializable types (mark as incomparable)
  - Do NOT ignore NaN differences

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Type comparison logic
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T7, T8, T10-T15)
  - **Parallel Group**: Wave 2
  - **Blocks**: T14 (LLM optimizer needs equivalence check)
  - **Blocked By**: T1, T2

  **References**:
  - `numpy.isclose()` and `numpy.allclose()` documentation

  **Acceptance Criteria**:
  - [ ] `uv run pytest test/components/test_equivalence.py -v` passes
  - [ ] Floating-point tolerance works
  - [ ] NaN comparison handled
  - [ ] Non-serializable types don't crash

  **QA Scenarios**:
  ```
  Scenario: Compare float arrays with tolerance
    Tool: Bash
    Steps:
      1. Run equivalence check on [1.0, 1.000001] vs [1.0, 1.000002]
      2. Verify result is True (within tolerance)
      3. Run on [1.0, 2.0] vs [1.0, 1.01]
      4. Verify result is False (outside tolerance)
    Expected Result: Correct tolerance comparison
    Evidence: .sisyphus/evidence/task-09-equivalence.txt
  ```

  **Commit**: YES
  - Message: `feat(equivalence): add semantic equivalence checking`
  - Files: components/arwiz/equivalence/**, test/components/test_equivalence.py

---

- [x] 10. Input Manager Component

  **What to do**:
  - Create `components/arwiz/input_manager/` with standard Polylith pattern
  - Create `interface.py` with `InputManagerProtocol`:
    - `capture_inputs(function_call) -> InputSnapshot`
    - `store_input(snapshot, path) -> Path`
    - `load_input(path) -> InputSnapshot`
    - `replay_input(snapshot, function) -> Any`
  - Create `core.py` with `DefaultInputManager`:
    - Serialize args/kwargs to JSON (with pickle fallback for non-JSON)
    - Store with timestamp and content hash
    - Load and deserialize
    - Replay by calling function with stored args
  - Create `storage.py` for `.arwiz/inputs/` management
  - Write TDD tests in `test/components/test_input_manager.py`
  - Add brick to `[tool.polylith.bricks]`

  **Must NOT do**:
  - Do NOT store non-serializable inputs (skip with warning)
  - Do NOT modify user's code to capture inputs

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Serialization and storage logic
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T7-T9, T11-T15)
  - **Parallel Group**: Wave 2
  - **Blocks**: T11 (coverage tracer), T12 (decorator injector)
  - **Blocked By**: T1, T2

  **References**:
  - `pickle` and `json` stdlib documentation
  - `hashlib` for content hashing

  **Acceptance Criteria**:
  - [ ] `uv run pytest test/components/test_input_manager.py -v` passes
  - [ ] Inputs stored to `.arwiz/inputs/`
  - [ ] Replay produces same result as original call
  - [ ] Non-serializable inputs handled gracefully

  **QA Scenarios**:
  ```
  Scenario: Capture and replay input
    Tool: Bash
    Steps:
      1. Capture input for function call with args (1, 2, 3)
      2. Store to .arwiz/inputs/
      3. Load and replay
      4. Verify same result
    Expected Result: Input captured, stored, replayed successfully
    Evidence: .sisyphus/evidence/task-10-input-manager.txt
  ```

  **Commit**: YES
  - Message: `feat(input_manager): add input capture and replay`
  - Files: components/arwiz/input_manager/**, test/components/test_input_manager.py

---

- [x] 11. Coverage Tracer Component

  **What to do**:
  - Create `components/arwiz/coverage_tracer/` with standard Polylith pattern
  - Create `interface.py` with `CoverageTracerProtocol`:
    - `trace_branches(script_path, args) -> BranchCoverage`
    - `get_uncovered_branches(coverage) -> list[tuple[str, int]]`
  - Create `core.py` with `DefaultCoverageTracer`:
    - Use `sys.settrace` for runtime branch tracing
    - Track line numbers and branches taken
    - Identify uncovered branches
    - Store coverage data for comparison
  - Create `ast_analyzer.py` for static branch detection:
    - Parse AST to find all if/elif/else, for, while, try/except
    - Compare runtime branches vs static branches
  - Write TDD tests in `test/components/test_coverage_tracer.py`
  - Add brick to `[tool.polylith.bricks]`

  **Must NOT do**:
  - Do NOT use coverage.py library (implement ourselves for control)
  - Do NOT trace into C extensions

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: sys.settrace is complex, requires careful handling
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T7-T10, T12-T15)
  - **Parallel Group**: Wave 2
  - **Blocks**: T16 (CLI), T19 (Orchestrator)
  - **Blocked By**: T1, T2, T10

  **References**:
  - Python `sys.settrace` documentation
  - Python `ast` module documentation
  - `coverage.py` source code for reference (don't use directly)

  **Acceptance Criteria**:
  - [ ] `uv run pytest test/components/test_coverage_tracer.py -v` passes
  - [ ] Branch coverage percentage calculated
  - [ ] Uncovered branches identified
  - [ ] Tracing overhead < 50%

  **QA Scenarios**:
  ```
  Scenario: Trace branching script
    Tool: Bash
    Steps:
      1. Run coverage tracer on branching.py fixture
      2. Verify branch coverage is calculated
      3. Verify uncovered branches are identified
    Expected Result: Coverage data with uncovered branches
    Evidence: .sisyphus/evidence/task-11-coverage-trace.txt
  ```

  **Commit**: YES
  - Message: `feat(coverage_tracer): add runtime branch tracing`
  - Files: components/arwiz/coverage_tracer/**, test/components/test_coverage_tracer.py

---

- [x] 12. Decorator Injector Component

  **What to do**:
  - Create `components/arwiz/decorator_injector/` with standard Polylith pattern
  - Create `interface.py` with `DecoratorInjectorProtocol`:
    - `inject_decorators(source_path, decorators) -> Path` (returns temp path)
    - `create_input_override_decorator(input_snapshot) -> Callable`
  - Create `core.py` with `DefaultDecoratorInjector`:
    - Parse source file with `ast.parse`
    - Inject `@arwiz_override_input` decorator at function definitions
    - Write modified AST to temp file
    - Preserve original formatting where possible
  - Create `import_hook.py` for `sys.meta_path` injection:
    - Intercept imports and wrap functions
    - Apply decorators dynamically
  - Write TDD tests in `test/components/test_decorator_injector.py`
  - Add brick to `[tool.polylith.bricks]`

  **Must NOT do**:
  - Do NOT modify user's original source file (only temp copies)
  - Do NOT break async generators (handle gracefully)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: AST manipulation is complex and error-prone
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T7-T11, T13-T15)
  - **Parallel Group**: Wave 2
  - **Blocks**: T16 (CLI), T19 (Orchestrator)
  - **Blocked By**: T1, T2, T10

  **References**:
  - Python `ast` module documentation
  - `ast.NodeTransformer` for AST modification
  - `ast.unparse` for converting AST back to source

  **Acceptance Criteria**:
  - [ ] `uv run pytest test/components/test_decorator_injector.py -v` passes
  - [ ] Decorators injected without breaking valid Python
  - [ ] Temp file created, original untouched
  - [ ] Import hook works for module wrapping

  **QA Scenarios**:
  ```
  Scenario: Inject decorator into script
    Tool: Bash
    Steps:
      1. Run decorator injector on simple_loop.py
      2. Verify temp file has @arwiz_override_input decorator
      3. Verify original file is unchanged
    Expected Result: Decorated temp file created
    Evidence: .sisyphus/evidence/task-12-decorator-inject.txt
  ```

  **Commit**: YES
  - Message: `feat(decorator_injector): add AST-based decorator injection`
  - Files: components/arwiz/decorator_injector/**, test/components/test_decorator_injector.py

---

- [x] 13. Hot-Reload Component

  **What to do**:
  - Create `components/arwiz/hot_reload/` with standard Polylith pattern
  - Create `interface.py` with `HotReloadProtocol`:
    - `reload_function(module_path, function_name, new_source) -> bool`
    - `create_function_wrapper(original, optimized) -> Callable`
    - `rollback(module_path, function_name) -> None`
  - Create `core.py` with `DefaultHotReloader`:
    - Mode 1: Function args/returns capture (via wrapper)
    - Mode 2: Full function replacement (via `sys.modules`)
    - Mode 3: Variable injection (via `ctypes` frame manipulation - CPython 3.13 only)
    - Store original function for rollback
    - Validate function signature matches
  - Create `frame_manipulation.py` for CPython-specific variable injection:
    - Use `ctypes.pythonapi.PyFrame_LocalsToFast`
    - Document CPython version dependency
  - Write TDD tests in `test/components/test_hot_reload.py`
  - Add brick to `[tool.polylith.bricks]`

  **Must NOT do**:
  - Do NOT reload in arwiz process (use subprocess with process_manager)
  - Do NOT support async generators in v0.1

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: ctypes frame manipulation is fragile and version-specific
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T7-T12, T14-T15)
  - **Parallel Group**: Wave 2
  - **Blocks**: T14 (LLM optimizer applies via hot-reload)
  - **Blocked By**: T1, T2

  **References**:
  - `importlib.reload` documentation
  - `ctypes.pythonapi` for CPython internals
  - CPython source for `PyFrame_LocalsToFast`

  **Acceptance Criteria**:
  - [ ] `uv run pytest test/components/test_hot_reload.py -v` passes
  - [ ] Function replacement works (Mode 2)
  - [ ] Rollback restores original function
  - [ ] Variable injection works on CPython 3.13

  **QA Scenarios**:
  ```
  Scenario: Hot-reload function
    Tool: Bash
    Steps:
      1. Hot-reload simple_loop function with optimized version
      2. Verify new function is called
      3. Rollback and verify original is restored
    Expected Result: Function swapped and restored
    Evidence: .sisyphus/evidence/task-13-hot-reload.txt
  ```

  **Commit**: YES
  - Message: `feat(hot_reload): add function replacement and rollback`
  - Files: components/arwiz/hot_reload/**, test/components/test_hot_reload.py

---

- [x] 14. LLM Optimizer Component

  **What to do**:
  - Create `components/arwiz/llm_optimizer/` with standard Polylith pattern
  - Create `interface.py` with `LLMOptimizerProtocol`:
    - `optimize_function(source_code, hotspot_info, config) -> OptimizationAttempt`
    - `generate_optimization_prompt(source, hotspot) -> str`
    - `parse_llm_response(response) -> str` (extract code from markdown)
  - Create `core.py` with `DefaultLLMOptimizer`:
    - Support OpenAI API (gpt-4, gpt-4o)
    - Support Anthropic API (claude-3.5-sonnet)
    - Support local models via Ollama (llama3, mistral)
    - Build optimization prompt with:
      - Original function source
      - Profiling data (time spent, call count)
      - Desired optimization strategy (vectorize, numba, etc.)
    - Parse response to extract code block
    - Validate generated code (syntax check)
  - Create `prompts.py` with prompt templates:
    - Vectorization prompt (for loops → numpy)
    - Numba JIT prompt (add @jit decorator)
    - Caching prompt (memoization)
    - Batch I/O prompt (accumulate writes)
  - Create `providers.py` for API clients:
    - `OpenAIProvider`, `AnthropicProvider`, `OllamaProvider`
  - Write TDD tests in `test/components/test_llm_optimizer.py`
  - Add brick to `[tool.polylith.bricks]`

  **Must NOT do**:
  - Do NOT auto-apply LLM-generated code without validation
  - Do NOT require API key (template fallback if unavailable)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: LLM integration, prompt engineering, response parsing
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T7-T13, T15)
  - **Parallel Group**: Wave 2
  - **Blocks**: T16 (CLI), T17 (Streamlit), T19 (Orchestrator)
  - **Blocked By**: T1, T2, T8 (hotspots), T9 (equivalence), T13 (hot-reload)

  **References**:
  - OpenAI API documentation
  - Anthropic API documentation
  - Ollama API documentation

  **Acceptance Criteria**:
  - [ ] `uv run pytest test/components/test_llm_optimizer.py -v` passes
  - [ ] OpenAI API integration works (with mock)
  - [ ] Prompt templates generate valid prompts
  - [ ] Response parsing extracts code correctly
  - [ ] Syntax validation catches invalid code

  **QA Scenarios**:
  ```
  Scenario: LLM generates vectorized code
    Tool: Bash
    Steps:
      1. Call optimize_function with loop-based code
      2. Mock LLM response with vectorized version
      3. Verify parsed code is valid Python
    Expected Result: Optimized code extracted
    Evidence: .sisyphus/evidence/task-14-llm-optimize.txt
  ```

  **Commit**: YES
  - Message: `feat(llm_optimizer): add AI-assisted optimization generation`
  - Files: components/arwiz/llm_optimizer/**, test/components/test_llm_optimizer.py

---

- [x] 15. Template Optimizer Component

  **What to do**:
  - Create `components/arwiz/template_optimizer/` with standard Polylith pattern
  - Create `interface.py` with `TemplateOptimizerProtocol`:
    - `apply_template(source_code, template_name) -> str`
    - `list_templates() -> list[str]`
    - `detect_applicable_templates(source, hotspot) -> list[str]`
  - Create `core.py` with `DefaultTemplateOptimizer`:
    - Templates as Python functions that transform AST
    - Template registry with metadata (applicable patterns)
  - Create `templates/` subpackage:
    - `vectorize_loop.py`: for i loop → np.where / np.vectorize
    - `numba_jit.py`: add @njit decorator, handle types
    - `add_caching.py`: wrap with @lru_cache or memo dict
    - `batch_io.py`: accumulate writes, batch at end
  - Create `pattern_detection.py`:
    - Detect loop patterns (range, enumerate, while)
    - Detect pandas operations
    - Detect file I/O patterns
  - Write TDD tests in `test/components/test_template_optimizer.py`
  - Add brick to `[tool.polylith.bricks]`

  **Must NOT do**:
  - Do NOT use regex for code transformation (use AST)
  - Do NOT assume all templates apply to all code

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Template-based transformations, well-defined patterns
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T7-T14)
  - **Parallel Group**: Wave 2
  - **Blocks**: T14 (LLM can fall back to templates), T19 (Orchestrator)
  - **Blocked By**: T1, T2, T9 (equivalence check)

  **References**:
  - Python `ast` module for AST transformation
  - Performance-profiling skill for optimization patterns

  **Acceptance Criteria**:
  - [ ] `uv run pytest test/components/test_template_optimizer.py -v` passes
  - [ ] Vectorize template transforms for loops
  - [ ] Numba template adds @njit correctly
  - [ ] Pattern detection identifies applicable templates

  **QA Scenarios**:
  ```
  Scenario: Apply vectorization template
    Tool: Bash
    Steps:
      1. Run apply_template with vectorize_loop on simple_loop.py
      2. Verify output uses np.where or np.vectorize
      3. Verify output is valid Python
    Expected Result: Vectorized code generated
    Evidence: .sisyphus/evidence/task-15-template.txt
  ```

  **Commit**: YES
  - Message: `feat(template_optimizer): add optimization templates`
  - Files: components/arwiz/template_optimizer/**, test/components/test_template_optimizer.py

---

### Wave 3: Entry Points

- [x] 16. CLI Base (Click Commands)

  **What to do**:
  - Create `bases/arwiz/cli/` directory structure
  - Create `bases/arwiz/cli/__init__.py` with Click group
  - Create `bases/arwiz/cli/core.py` with commands:
    - `arwiz profile <script> [--args ...] [--output PATH] [--line]`
    - `arwiz optimize <script> --function <name> [--strategy auto|llm|template]`
    - `arwiz coverage <script> [--args ...] [--store-inputs]`
    - `arwiz report <profile> [--format json|text|html]`
  - Create `commands/` subpackage with command implementations:
    - `profile_cmd.py`: Run profiler, output results
    - `optimize_cmd.py`: Profile → hotspot → optimize → apply → verify
    - `coverage_cmd.py`: Run tracer → store inputs
    - `report_cmd.py`: Load profile, format output
  - Register entry point in `pyproject.toml`:
    ```toml
    [project.scripts]
    arwiz = "arwiz.cli:main"
    ```
  - Write TDD tests in `test/bases/test_cli.py`
  - Add brick to `[tool.polylith.bricks]`

  **Must NOT do**:
  - Do NOT run target scripts in CLI process
  - Do NOT auto-apply optimizations without user confirmation

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Click CLI is straightforward, delegates to components
  - **Skills**: [`conventional-commits`]

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T17, T18, T19)
  - **Parallel Group**: Wave 3
  - **Blocks**: T19 (Orchestrator uses CLI)
  - **Blocked By**: T7 (profiler), T8 (hotspot), T11 (coverage), T14 (LLM optimizer)

  **References**:
  - Click documentation for CLI building
  - `~/wsp/trading-bot/bases/trading_bot/streamlit_backtest/` for base structure

  **Acceptance Criteria**:
  - [ ] `uv run arwiz --help` shows commands
  - [ ] `uv run arwiz profile <script>` produces output
  - [ ] `uv run arwiz optimize <script> --function <name>` runs optimization
  - [ ] `uv run arwiz coverage <script>` stores inputs

  **QA Scenarios**:
  ```
  Scenario: CLI profile command
    Tool: Bash
    Steps:
      1. Run `uv run arwiz profile test/fixtures/targets/simple_loop.py`
      2. Check exit code is 0
      3. Verify JSON output contains hotspots
    Expected Result: Profile output printed
    Evidence: .sisyphus/evidence/task-16-cli-profile.txt

  Scenario: CLI optimize command
    Tool: Bash
    Steps:
      1. Run `uv run arwiz optimize test/fixtures/targets/simple_loop.py --function main --strategy template`
      2. Check exit code is 0
      3. Verify optimization was applied
    Expected Result: Optimization successful
    Evidence: .sisyphus/evidence/task-16-cli-optimize.txt
  ```

  **Commit**: YES
  - Message: `feat(cli): add Click CLI commands`
  - Files: bases/arwiz/cli/**, test/bases/test_cli.py

---

- [x] 17. Streamlit UI Base

  **What to do**:
  - Create `bases/arwiz/streamlit_ui/` directory structure
  - Create `bases/arwiz/streamlit_ui/__init__.py`
  - Create `bases/arwiz/streamlit_ui/app.py` with Streamlit app:
    - Sidebar: Script selection, config options
    - Tab 1: Profiling - flame graph (plotly), call tree, hotspots table
    - Tab 2: Optimization - code diff view, speedup metrics, apply button
    - Tab 3: Coverage - branch coverage visualization, input samples
  - Create `components/` subpackage for UI components:
    - `flame_graph.py`: Plotly-based flame graph
    - `code_diff.py`: Side-by-side diff viewer
    - `metrics_display.py`: Speedup, equivalence results
  - Create `state.py` for session state management
  - Add Streamlit to dependencies in pyproject.toml
  - Write TDD tests in `test/bases/test_streamlit_ui.py`
  - Add brick to `[tool.polylith.bricks]`

  **Must NOT do**:
  - Do NOT embed secrets in UI (use env vars for API keys)
  - Do NOT block UI thread on long operations (use asyncio/threads)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: UI/UX, Plotly visualizations, Streamlit patterns
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T16, T18, T19)
  - **Parallel Group**: Wave 3
  - **Blocks**: T22 (smoke tests)
  - **Blocked By**: T7 (profiler), T8 (hotspot), T14 (LLM optimizer)

  **References**:
  - Streamlit documentation
  - Plotly documentation for flame graphs
  - `streamlit-ace` for code display

  **Acceptance Criteria**:
  - [ ] `uv run streamlit run bases/arwiz/streamlit_ui/app.py` starts
  - [ ] Flame graph displays profile data
  - [ ] Code diff shows original vs optimized
  - [ ] Apply button triggers hot-reload

  **QA Scenarios**:
  ```
  Scenario: Streamlit UI loads
    Tool: Playwright
    Steps:
      1. Start streamlit app
      2. Navigate to http://localhost:8501
      3. Verify sidebar is visible
      4. Verify tabs are rendered
    Expected Result: UI renders correctly
    Evidence: .sisyphus/evidence/task-17-streamlit-ui.png
  ```

  **Commit**: YES
  - Message: `feat(streamlit_ui): add visualization dashboard`
  - Files: bases/arwiz/streamlit_ui/**, test/bases/test_streamlit_ui.py

---

- [x] 18. FastAPI Endpoint Base

  **What to do**:
  - Create `bases/arwiz/api/` directory structure
  - Create `bases/arwiz/api/__init__.py` with FastAPI app
  - Create `bases/arwiz/api/routes/` subpackage:
    - `profile.py`: POST /profile - run profiler, return JSON
    - `optimize.py`: POST /optimize - run optimizer, return diff
    - `coverage.py`: POST /coverage - run tracer, return coverage
    - `health.py`: GET /health - health check
  - Create `models.py` with Pydantic request/response models:
    - `ProfileRequest`, `ProfileResponse`
    - `OptimizeRequest`, `OptimizeResponse`
    - `CoverageRequest`, `CoverageResponse`
  - Add FastAPI and uvicorn to dependencies
  - Write TDD tests in `test/bases/test_api.py`
  - Add brick to `[tool.polylith.bricks]`

  **Must NOT do**:
  - Do NOT expose API keys in responses
  - Do NOT allow arbitrary code execution without sandboxing

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Standard FastAPI patterns
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T16, T17, T19)
  - **Parallel Group**: Wave 3
  - **Blocks**: T22 (smoke tests)
  - **Blocked By**: T7 (profiler), T8 (hotspot), T14 (LLM optimizer)

  **References**:
  - FastAPI documentation
  - `~/wsp/trading-bot/bases/trading_bot/research/` for API patterns

  **Acceptance Criteria**:
  - [ ] `uv run uvicorn arwiz.api:app` starts
  - [ ] POST /profile returns profile data
  - [ ] POST /optimize returns optimization result
  - [ ] GET /health returns 200

  **QA Scenarios**:
  ```
  Scenario: API profile endpoint
    Tool: Bash (curl)
    Steps:
      1. Start FastAPI server
      2. POST to /profile with script path
      3. Verify 200 response with profile data
    Expected Result: Profile data in response
    Evidence: .sisyphus/evidence/task-18-api-profile.txt
  ```

  **Commit**: YES
  - Message: `feat(api): add FastAPI endpoints`
  - Files: bases/arwiz/api/**, test/bases/test_api.py

---

- [x] 19. Orchestrator Component

  **What to do**:
  - Create `components/arwiz/orchestrator/` with standard Polylith pattern
  - Create `interface.py` with `OrchestratorProtocol`:
    - `run_profile_optimize_pipeline(script, function, config) -> OptimizationResult`
    - `run_coverage_replay_pipeline(script, config) -> CoverageResult`
  - Create `core.py` with `DefaultOrchestrator`:
    - Profile → Optimize pipeline:
      1. Profile script
      2. Detect hotspots
      3. Generate optimization (LLM or template)
      4. Validate syntax
      5. Check equivalence on sample inputs
      6. Hot-reload optimized function
      7. Re-profile to measure speedup
      8. Rollback if speedup < 50%
    - Coverage → Replay pipeline:
      1. Trace branches
      2. Capture inputs for each branch
      3. Store inputs
      4. Allow replay against modified code
  - Create `pipeline_state.py` for tracking pipeline progress
  - Write TDD tests in `test/components/test_orchestrator.py`
  - Add brick to `[tool.polylith.bricks]`

  **Must NOT do**:
  - Do NOT run pipelines in arwiz process (use process_manager)
  - Do NOT skip equivalence check before hot-reload

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex pipeline coordination, error handling
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T16, T17, T18)
  - **Parallel Group**: Wave 3
  - **Blocks**: T20, T21, T22 (integration tests)
  - **Blocked By**: T7-T16 (all core components)

  **References**:
  - Workflow patterns from requirements

  **Acceptance Criteria**:
  - [ ] `uv run pytest test/components/test_orchestrator.py -v` passes
  - [ ] Profile-optimize pipeline completes end-to-end
  - [ ] Coverage-replay pipeline completes end-to-end
  - [ ] Pipeline handles errors gracefully

  **QA Scenarios**:
  ```
  Scenario: Full optimization pipeline
    Tool: Bash
    Steps:
      1. Run orchestrator on simple_loop.py with main function
      2. Verify profiling step completes
      3. Verify hotspot detected
      4. Verify optimization generated
      5. Verify equivalence checked
      6. Verify speedup measured
    Expected Result: Complete pipeline run
    Evidence: .sisyphus/evidence/task-19-orchestrator.txt
  ```

  **Commit**: YES
  - Message: `feat(orchestrator): add pipeline coordination`
  - Files: components/arwiz/orchestrator/**, test/components/test_orchestrator.py

---

### Wave 4: Integration

- [ ] 20. Profile → Optimize Pipeline Integration

  **What to do**:
  - Create `test/integration/test_profile_optimize.py`
  - Test full pipeline: profile → hotspot → optimize → verify → apply
  - Test with each target fixture:
    - simple_loop.py → vectorization
    - numpy_heavy.py → numba JIT
    - io_bound.py → batch I/O
  - Test rollback scenarios:
    - Optimization breaks semantics
    - Speedup < 50%
    - Syntax error in generated code
  - Test error handling:
    - Target script crashes
    - LLM API timeout
    - Memory limit exceeded
  - Verify evidence capture at each step

  **Must NOT do**:
  - Do NOT skip any pipeline step in tests

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Integration testing requires full system
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T21, T22)
  - **Parallel Group**: Wave 4
  - **Blocks**: F1-F4 (final verification)
  - **Blocked By**: T19 (orchestrator), T16 (CLI)

  **References**:
  - Test fixtures from T4

  **Acceptance Criteria**:
  - [ ] `uv run pytest test/integration/test_profile_optimize.py -v` passes
  - [ ] All target fixtures successfully optimized
  - [ ] Rollback scenarios handled correctly
  - [ ] Error scenarios don't crash arwiz

  **QA Scenarios**:
  ```
  Scenario: End-to-end optimization
    Tool: Bash
    Steps:
      1. Run `uv run arwiz optimize test/fixtures/targets/simple_loop.py --function main`
      2. Verify optimization applied
      3. Verify speedup > 50%
    Expected Result: Successful optimization
    Evidence: .sisyphus/evidence/task-20-e2e-optimize.txt
  ```

  **Commit**: YES
  - Message: `test(integration): add profile-optimize pipeline tests`
  - Files: test/integration/test_profile_optimize.py

---

- [ ] 21. Coverage → Replay Pipeline Integration

  **What to do**:
  - Create `test/integration/test_coverage_replay.py`
  - Test full pipeline: trace → capture → store → replay
  - Test with branching.py fixture:
    - Verify all branches detected
    - Verify inputs captured for each branch
    - Verify replay produces same results
  - Test with modified code:
    - Modify function implementation
    - Replay stored inputs
    - Verify new results (or same if semantic-preserving)
  - Test edge cases:
    - Non-serializable inputs
    - Large inputs (disk space)
    - Rapid input capture

  **Must NOT do**:
  - Do NOT skip branch coverage verification

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Integration testing requires full system
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T20, T22)
  - **Parallel Group**: Wave 4
  - **Blocks**: F1-F4 (final verification)
  - **Blocked By**: T19 (orchestrator), T16 (CLI)

  **References**:
  - Test fixtures from T4

  **Acceptance Criteria**:
  - [ ] `uv run pytest test/integration/test_coverage_replay.py -v` passes
  - [ ] Branch coverage calculated correctly
  - [ ] Inputs captured and stored
  - [ ] Replay works with modified code

  **QA Scenarios**:
  ```
  Scenario: Coverage and replay
    Tool: Bash
    Steps:
      1. Run `uv run arwiz coverage test/fixtures/targets/branching.py --store-inputs`
      2. Verify inputs stored in .arwiz/inputs/
      3. Verify branch coverage reported
    Expected Result: Coverage captured
    Evidence: .sisyphus/evidence/task-21-coverage.txt
  ```

  **Commit**: YES
  - Message: `test(integration): add coverage-replay pipeline tests`
  - Files: test/integration/test_coverage_replay.py

---

- [ ] 22. End-to-End Smoke Tests

  **What to do**:
  - Create `test/integration/test_smoke.py`
  - Test all three entry points:
    - CLI: `arwiz profile`, `arwiz optimize`, `arwiz coverage`
    - Streamlit: Start app, verify pages load
    - FastAPI: Start server, verify endpoints respond
  - Test with real LLM (if API key available) or mock
  - Test full user workflow:
    1. Profile a script
    2. Identify bottleneck
    3. Generate optimization
    4. Apply and verify
    5. Report results
  - Capture timing metrics

  **Must NOT do**:
  - Do NOT require API keys for tests (mock when unavailable)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: E2E testing requires all systems working
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T20, T21)
  - **Parallel Group**: Wave 4
  - **Blocks**: F1-F4 (final verification)
  - **Blocked By**: T16-T19 (all entry points)

  **References**:
  - All components

  **Acceptance Criteria**:
  - [ ] `uv run pytest test/integration/test_smoke.py -v` passes
  - [ ] All entry points accessible
  - [ ] Full workflow completes

  **QA Scenarios**:
  ```
  Scenario: Full user workflow via CLI
    Tool: Bash
    Steps:
      1. `uv run arwiz profile test/fixtures/targets/simple_loop.py -o profile.json`
      2. `uv run arwiz optimize test/fixtures/targets/simple_loop.py -f main`
      3. `uv run arwiz report profile.json`
    Expected Result: Complete workflow
    Evidence: .sisyphus/evidence/task-22-smoke.txt
  ```

  **Commit**: YES
  - Message: `test(smoke): add end-to-end smoke tests`
  - Files: test/integration/test_smoke.py

---

## Final Verification Wave (MANDATORY)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists. For each "Must NOT Have": search codebase for forbidden patterns. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  
  **Checklist**:
  - [ ] Subprocess execution (not in-process)
  - [ ] User approval before optimization apply
  - [ ] Original source files never modified
  - [ ] Foundation has zero external deps
  - [ ] All components have interface.py + core.py
  
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [22/22] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `tsc --noEmit` equivalent (`pyrefly check`), ruff lint + format, `uv run pytest --cov`.
  
  **Checklist**:
  - [ ] `uv run pyrefly check .` → PASS
  - [ ] `uv run ruff check .` → PASS
  - [ ] `uv run ruff format --check .` → PASS
  - [ ] `uv run pytest --cov` → >80% coverage
  - [ ] No `as any`, `# type: ignore` without justification
  - [ ] No empty except blocks
  - [ ] No console.log in production code
  
  Output: `Type [PASS/FAIL] | Lint [PASS/FAIL] | Format [PASS/FAIL] | Tests [N pass/N fail] | Coverage [N%] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high` (+ `playwright` skill for Streamlit)
  Start from clean state. Execute key QA scenarios from tasks. Test cross-component integration. Save to `.sisyphus/evidence/final-qa/`.
  
  **Scenarios to Execute**:
  - [ ] CLI profile command on simple_loop.py
  - [ ] CLI optimize command with template strategy
  - [ ] CLI coverage command on branching.py
  - [ ] Streamlit UI loads and displays profile
  - [ ] FastAPI /profile endpoint returns data
  - [ ] Rollback works when optimization fails
  
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff. Verify 1:1 — everything in spec was built, nothing beyond spec. Check "Must NOT do" compliance. Detect cross-task contamination.
  
  **Checklist**:
  - [ ] All 22 tasks implemented as specified
  - [ ] No Rust components in v0.1
  - [ ] No async/threading support (documented as limitation)
  - [ ] No in-process execution
  - [ ] No auto-apply without user approval
  
  Output: `Tasks [22/22 compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

| Commit | Message | Files | Pre-commit |
|--------|---------|-------|------------|
| 1 | `chore(init): initialize arwiz polylith workspace` | workspace.toml, pyproject.toml, .gitignore, .python-version, .pre-commit-config.yaml, directories | None |
| 2 | `feat(foundation): add core type definitions` | components/arwiz/foundation/**, test/foundation/** | `uv run pyrefly check` |
| 3 | `test(architecture): add AST-based validation tests` | test/test_architecture.py | `uv run pytest test/test_architecture.py` |
| 4 | `test(fixtures): add sample target scripts for testing` | test/fixtures/** | `uv run python -m py_compile test/fixtures/targets/*.py` |
| 5 | `feat(process_manager): add subprocess execution with limits` | components/arwiz/process_manager/**, test/components/test_process_manager.py | `uv run pytest test/components/test_process_manager.py` |
| 6 | `feat(config): add configuration loading with auto-detection` | components/arwiz/config/**, test/components/test_config.py | `uv run pytest test/components/test_config.py` |
| 7 | `feat(profiler): add cProfile and line_profiler integration` | components/arwiz/profiler/**, test/components/test_profiler.py | `uv run pytest test/components/test_profiler.py` |
| 8 | `feat(hotspot): add bottleneck identification` | components/arwiz/hotspot/**, test/components/test_hotspot.py | `uv run pytest test/components/test_hotspot.py` |
| 9 | `feat(equivalence): add semantic equivalence checking` | components/arwiz/equivalence/**, test/components/test_equivalence.py | `uv run pytest test/components/test_equivalence.py` |
| 10 | `feat(input_manager): add input capture and replay` | components/arwiz/input_manager/**, test/components/test_input_manager.py | `uv run pytest test/components/test_input_manager.py` |
| 11 | `feat(coverage_tracer): add runtime branch tracing` | components/arwiz/coverage_tracer/**, test/components/test_coverage_tracer.py | `uv run pytest test/components/test_coverage_tracer.py` |
| 12 | `feat(decorator_injector): add AST-based decorator injection` | components/arwiz/decorator_injector/**, test/components/test_decorator_injector.py | `uv run pytest test/components/test_decorator_injector.py` |
| 13 | `feat(hot_reload): add function replacement and rollback` | components/arwiz/hot_reload/**, test/components/test_hot_reload.py | `uv run pytest test/components/test_hot_reload.py` |
| 14 | `feat(llm_optimizer): add AI-assisted optimization generation` | components/arwiz/llm_optimizer/**, test/components/test_llm_optimizer.py | `uv run pytest test/components/test_llm_optimizer.py` |
| 15 | `feat(template_optimizer): add optimization templates` | components/arwiz/template_optimizer/**, test/components/test_template_optimizer.py | `uv run pytest test/components/test_template_optimizer.py` |
| 16 | `feat(cli): add Click CLI commands` | bases/arwiz/cli/**, test/bases/test_cli.py | `uv run pytest test/bases/test_cli.py` |
| 17 | `feat(streamlit_ui): add visualization dashboard` | bases/arwiz/streamlit_ui/**, test/bases/test_streamlit_ui.py | `uv run pytest test/bases/test_streamlit_ui.py` |
| 18 | `feat(api): add FastAPI endpoints` | bases/arwiz/api/**, test/bases/test_api.py | `uv run pytest test/bases/test_api.py` |
| 19 | `feat(orchestrator): add pipeline coordination` | components/arwiz/orchestrator/**, test/components/test_orchestrator.py | `uv run pytest test/components/test_orchestrator.py` |
| 20 | `test(integration): add profile-optimize pipeline tests` | test/integration/test_profile_optimize.py | `uv run pytest test/integration/test_profile_optimize.py` |
| 21 | `test(integration): add coverage-replay pipeline tests` | test/integration/test_coverage_replay.py | `uv run pytest test/integration/test_coverage_replay.py` |
| 22 | `test(smoke): add end-to-end smoke tests` | test/integration/test_smoke.py | `uv run pytest test/integration/test_smoke.py` |

---

## Success Criteria

### Verification Commands
```bash
# Type checking
uv run pyrefly check .  # Expected: 0 errors

# Linting
uv run ruff check .     # Expected: 0 violations
uv run ruff format --check .  # Expected: all files formatted

# Tests
uv run pytest           # Expected: all tests pass
uv run pytest --cov     # Expected: >80% coverage

# Architecture
uv run pytest test/test_architecture.py  # Expected: all rules pass

# CLI
uv run arwiz --help     # Expected: show commands
uv run arwiz profile test/fixtures/targets/simple_loop.py  # Expected: profile output

# Streamlit
uv run streamlit run bases/arwiz/streamlit_ui/app.py  # Expected: UI loads

# FastAPI
uv run uvicorn arwiz.api:app  # Expected: server starts
curl http://localhost:8000/health  # Expected: {"status": "ok"}
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All 22 tasks completed
- [ ] All tests pass (>80% coverage)
- [ ] Architecture validation passes
- [ ] CLI commands work
- [ ] Streamlit UI loads
- [ ] FastAPI endpoints respond
- [ ] Profile → Optimize pipeline works
- [ ] Coverage → Replay pipeline works
- [ ] User approval obtained for final sign-off


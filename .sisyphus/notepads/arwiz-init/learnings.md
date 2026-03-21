# Arwiz-Init Learnings

## Task 1: Polylith Workspace Scaffolding

- workspace.toml mirrors trading-bot exactly, just namespace changed to "arwiz"
- pyproject.toml: `[tool.polylith.bricks]` section intentionally empty — bricks added by later tasks
- No `ignore` list in ruff config (trading-bot has E501/B008 ignored, arwiz starts clean)
- `uv sync` resolved 78 packages and installed 77 (arwiz itself built from local)
- `uv run ruff check .` passes with zero files to check (no .py files yet)
- No `__init__.py` files in `bases/arwiz/` or `components/arwiz/` — PEP 420 compliance
- `.arwiz/` directory created but also in .gitignore (runtime/cache data, not source)
- `.gitignore` omits trading-bot-specific entries: `skills/`, `backtest_engine_rust` source, jupyter dev dep
- Added `psutil`, `httpx`, `rich`, `click` as arwiz-specific deps (profiling/CLI tool)

## Task 2: LLM Optimizer + Template Optimizer

- Added `llm_optimizer` brick with `interface.py`, `core.py`, `prompts.py`, `providers.py`, and package `__init__.py`.
- `DefaultLLMOptimizer.optimize_function` now follows prompt -> provider call -> parse -> syntax validation -> `OptimizationAttempt` flow.
- Provider layer supports OpenAI, Anthropic, and Ollama via `httpx` with `get_provider(config)` factory.
- Added `template_optimizer` brick with AST-based detection/transforms only (no regex transforms).
- Implemented template modules: vectorize loop, numba jit decorator injection, lru_cache decorator injection, batch I/O rewrite.
- Implemented AST detectors: for-loops, pandas apply/iterrows calls, file I/O calls in loops.
- Registered both new bricks in `[tool.polylith.bricks]`.
- Verified targeted tests pass: `uv run pytest test/components/test_llm_optimizer.py test/components/test_template_optimizer.py`.
- Verified LSP diagnostics clean for changed component and test files.

## Task 14-15: LLM + Template Optimizers

- `llm_optimizer/core.py` now implements provider factory selection, strategy-aware prompt generation, markdown/plain response parsing, syntax validation via `compile`, and `OptimizationAttempt` construction with `strategy="llm_generated"`.
- LLM optimizer tests were rewritten to focus on core behavior with mock providers (no API keys/network), including valid/invalid generation paths.
- `template_optimizer` now exposes required protocol + core + template registry with sorted template listing and applicability detection via lightweight pattern checks.
- Template functions were aligned to required names (`vectorize_loop`, `add_numba_jit`, `add_caching`, `batch_io`) and keep AST-based transformations for code mutation tasks.
- Added missing bricks to `[tool.polylith.bricks]`: `components/arwiz/llm_optimizer` and `components/arwiz/template_optimizer`.
- Validation snapshot: `uv run pytest` passes fully (185 tests), and changed-file LSP diagnostics report no errors.


## Task 18: FastAPI Endpoint Base

- Created `bases/arwiz/api/` with FastAPI app, 4 route modules, Pydantic models, and tests.
- PEP 420: `bases/arwiz/` has NO `__init__.py` — only `bases/arwiz/api/` has one.
- Route files need top-level imports (not deferred inside functions) so `unittest.mock.patch` can find them for testing.
- `Path.read_text()` in Python 3.13 uses C implementation — patching `builtins.open` doesn't work; use `patch.object(Path, "read_text")` instead.
- Tests use `starlette.testclient.TestClient` (synchronous) for simplicity, with `pytest.mark.skipif` when fastapi not installed.
- fastapi/uvicorn/starlette not yet in dependencies — tests verified via `uv run --with fastapi --with starlette --with httpx pytest`.
- Needed deps noted as TODO comment in `__init__.py`: `fastapi>=0.115.0`, `uvicorn>=0.34.0`.

## Task 17: Streamlit UI Base

- Created `bases/arwiz/streamlit_ui/` with 7 files: `__init__.py`, `app.py`, `state.py`, `components/__init__.py`, `components/flame_graph.py`, `components/code_diff.py`, `components/metrics_display.py`
- PEP 420: `bases/arwiz/` has NO `__init__.py` — only `bases/arwiz/streamlit_ui/` and `components/` subdirs have one
- App structure: sidebar (config) + 3 tabs (Profiling, Optimization, Coverage)
- `state.py` uses dataclass + `st.session_state` for caching between interactions
- `flame_graph.py`: Plotly-based flame graph via `go.Figure` + `go.Bar` (horizontal orientation)
- `code_diff.py`: Side-by-side diff viewer using `st.columns(2)`, line-by-line diff computation
- `metrics_display.py`: Speedup % formatting, color coding (green >=50%, lightgreen >=20%, gray >=0%, red <0%)
- Tests focus on component functions (not Streamlit rendering) — 30 tests covering state, flame graph, diff, metrics
- LSP errors for `arwiz.*` imports are false positives — polylith namespace resolution works at runtime
- Ruff C408: Use `{"key": "value"}` literals instead of `dict(key="value")` for Plotly layout dicts
- Run with: `streamlit run -m arwiz.streamlit_ui.app`

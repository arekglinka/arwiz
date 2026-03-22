import importlib.util
import re
from unittest.mock import MagicMock, patch

import pytest
from arwiz.foundation import OptimizationAttempt, OptimizationResult

fastapi_available = importlib.util.find_spec("fastapi") is not None
pytestmark = pytest.mark.skipif(not fastapi_available, reason="fastapi not installed")

if fastapi_available:
    from arwiz.api import app
    from starlette.testclient import TestClient


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def client_no_raise():
    return TestClient(app, raise_server_exceptions=False)


_FAKE_PROFILE_RESULT = MagicMock(
    profile_id="prof_123",
    duration_ms=150.5,
    hotspots=[],
    script_path="test.py",
    call_tree=None,
    raw_stats_path=None,
    timestamp="2026-01-01T00:00:00+00:00",
)

_FAKE_HOTSPOT = MagicMock(
    function_name="heavy_func",
    file_path="test.py",
    line_range=(10, 20),
    cumulative_time_ms=100.0,
    self_time_ms=80.0,
    call_count=50,
    is_c_extension=False,
    potential_speedup=2.0,
)
_FAKE_HOTSPOT.model_dump.return_value = {
    "function_name": "heavy_func",
    "file_path": "test.py",
    "line_range": (10, 20),
    "cumulative_time_ms": 100.0,
    "self_time_ms": 80.0,
    "call_count": 50,
    "is_c_extension": False,
    "potential_speedup": 2.0,
}

_FAKE_BRANCH_COVERAGE = MagicMock(
    total_branches=20,
    covered_branches=15,
    coverage_percent=75.0,
    uncovered_lines=[5, 10],
    branch_details=[],
    script_path="test.py",
    duration_ms=45.0,
)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"


@patch("arwiz.api.routes.profile.DefaultProfiler")
@patch("arwiz.api.routes.profile.DefaultHotspotDetector")
def test_profile(mock_detector_cls, mock_profiler_cls, client):
    mock_profiler_cls.return_value.profile_script.return_value = _FAKE_PROFILE_RESULT
    mock_detector_cls.return_value.detect_hotspots.return_value = [
        _FAKE_HOTSPOT,
    ]

    resp = client.post("/profile", json={"script_path": "test.py"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["profile_id"] == "prof_123"
    assert data["duration_ms"] == 150.5
    assert data["total_calls"] == 50
    assert len(data["hotspots"]) == 1
    assert data["hotspots"][0]["function_name"] == "heavy_func"


@patch("arwiz.api.routes.profile.DefaultProfiler")
def test_profile_with_args(mock_profiler_cls, client):
    mock_profiler_cls.return_value.profile_script.return_value = _FAKE_PROFILE_RESULT

    with patch("arwiz.api.routes.profile.DefaultHotspotDetector") as mock_det:
        mock_det.return_value.detect_hotspots.return_value = []
        resp = client.post(
            "/profile",
            json={"script_path": "test.py", "args": ["--flag"]},
        )

    assert resp.status_code == 200
    mock_profiler_cls.return_value.profile_script.assert_called_once_with(
        "test.py", args=["--flag"]
    )


@patch("arwiz.api.routes.optimize.DefaultOrchestrator")
def test_optimize_auto_strategy(mock_orch_cls, client):
    attempt = OptimizationAttempt(
        attempt_id="opt_123",
        original_code="def foo():\n    return [x**2 for x in range(10)]\n",
        optimized_code="@jit(nopython=True)\ndef foo():\n    return [x**2 for x in range(10)]\n",
        strategy="template",
        template_name="numba_jit",
        syntax_valid=True,
        passed_equivalence=True,
    )
    mock_orch = MagicMock()
    mock_orch.run_profile_optimize_pipeline.return_value = OptimizationResult(
        function_name="foo",
        file_path="test.py",
        attempts=[attempt],
        best_attempt=attempt,
        applied=True,
        total_time_saved_ms=0.0,
    )
    mock_orch_cls.return_value = mock_orch

    resp = client.post(
        "/optimize",
        json={
            "script_path": "test.py",
            "function_name": "foo",
            "strategy": "auto",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["function_name"] == "foo"
    assert data["best_attempt"]["syntax_valid"] is True
    assert "jit" in data["best_attempt"]["optimized_code"]


@patch("arwiz.api.routes.coverage.DefaultCoverageTracer")
def test_coverage(mock_tracer_cls, client):
    mock_tracer_cls.return_value.trace_branches.return_value = _FAKE_BRANCH_COVERAGE

    resp = client.post("/coverage", json={"script_path": "test.py", "args": ["--run"]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_branches"] == 20
    assert data["covered_branches"] == 15
    assert data["coverage_percent"] == 75.0


def test_profile_missing_script_path(client):
    resp = client.post("/profile", json={})
    assert resp.status_code == 422


@pytest.mark.integration
class TestErrorHandling:
    def test_profile_nonexistent_script(self, client_no_raise):
        """POST /profile with nonexistent script_path → 500."""
        with patch("arwiz.api.routes.profile.DefaultProfiler") as mock_p:
            mock_p.return_value.profile_script.side_effect = FileNotFoundError("No such file")
            resp = client_no_raise.post("/profile", json={"script_path": "/nonexistent/file.py"})
        assert resp.status_code == 500

    def test_profile_empty_script_path(self, client_no_raise):
        """POST /profile with empty string script_path → 500."""
        with patch("arwiz.api.routes.profile.DefaultProfiler") as mock_p:
            mock_p.return_value.profile_script.side_effect = ValueError(
                "script_path cannot be empty"
            )
            resp = client_no_raise.post("/profile", json={"script_path": ""})
        assert resp.status_code == 500

    def test_profile_args_wrong_type(self, client):
        """POST /profile with args as string instead of list → 422."""
        resp = client.post(
            "/profile",
            json={"script_path": "test.py", "args": "not-a-list"},
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert any("args" in str(e) for e in detail)

    def test_profile_wrong_method(self, client):
        """GET /profile (wrong HTTP method) → 405."""
        resp = client.get("/profile")
        assert resp.status_code == 405

    def test_optimize_missing_function_name(self, client):
        """POST /optimize without function_name → 422."""
        resp = client.post("/optimize", json={"script_path": "test.py"})
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert any("function_name" in str(e) for e in detail)

    def test_optimize_empty_body(self, client):
        """POST /optimize with empty body {} → 422."""
        resp = client.post("/optimize", json={})
        assert resp.status_code == 422

    def test_optimize_invalid_strategy(self, client_no_raise):
        """POST /optimize with unknown strategy → 500."""
        with patch("arwiz.api.routes.optimize.DefaultOrchestrator") as mock_orch_cls:
            mock_orch_cls.return_value.run_profile_optimize_pipeline.side_effect = ValueError(
                "Unknown strategy: bad_strategy"
            )
            resp = client_no_raise.post(
                "/optimize",
                json={
                    "script_path": "test.py",
                    "function_name": "foo",
                    "strategy": "bad_strategy",
                },
            )
        assert resp.status_code == 500

    def test_coverage_nonexistent_script(self, client_no_raise):
        """POST /coverage with nonexistent script_path → 500."""
        with patch("arwiz.api.routes.coverage.DefaultCoverageTracer") as mock_t:
            mock_t.return_value.trace_branches.side_effect = FileNotFoundError("No such file")
            resp = client_no_raise.post(
                "/coverage",
                json={"script_path": "/nonexistent/file.py"},
            )
        assert resp.status_code == 500

    def test_coverage_empty_body(self, client):
        """POST /coverage with empty body {} → 422."""
        resp = client.post("/coverage", json={})
        assert resp.status_code == 422

    def test_health_version_format(self, client):
        """GET /health returns semver-compatible version string."""
        resp = client.get("/health")
        assert resp.status_code == 200
        version = resp.json()["version"]
        assert re.match(r"\d+\.\d+\.\d+", version), f"Version '{version}' is not semver-like"

    def test_nonexistent_route_404(self, client):
        """GET /nonexistent → 404."""
        resp = client.get("/nonexistent")
        assert resp.status_code == 404

    def test_malformed_json_body(self, client):
        """POST with malformed JSON payload → 422."""
        resp = client.post(
            "/profile",
            content=b"this is not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

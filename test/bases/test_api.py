import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

fastapi_available = importlib.util.find_spec("fastapi") is not None
pytestmark = pytest.mark.skipif(not fastapi_available, reason="fastapi not installed")

if fastapi_available:
    from arwiz.api import app
    from starlette.testclient import TestClient


@pytest.fixture
def client():
    return TestClient(app)


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


@patch("arwiz.api.routes.optimize.DefaultTemplateOptimizer")
@patch.object(Path, "read_text")
def test_optimize_auto_strategy(mock_read_text, mock_optimizer_cls, client):
    fake_source = "def foo():\n    return [x**2 for x in range(10)]\n"
    mock_read_text.return_value = fake_source

    mock_optimizer_cls.return_value.apply_template.return_value = (
        "@jit(nopython=True)\ndef foo():\n    return [x**2 for x in range(10)]\n"
    )

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
    assert data["strategy"] == "numba_jit"
    assert data["syntax_valid"] is True
    assert "jit" in data["optimized_code"]


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

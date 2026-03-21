"""End-to-end smoke tests for arwiz.

Tests CLI, FastAPI, Streamlit, and orchestrator integration.
"""

import json
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "targets"


@pytest.mark.integration
class TestCLISmoke:
    """CLI smoke tests via subprocess invocation."""

    def test_cli_help(self) -> None:
        """arwiz --help runs without error."""
        result = subprocess.run(
            ["uv", "run", "arwiz", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "arwiz" in result.stdout.lower()

    @pytest.mark.slow
    def test_cli_profile(self) -> None:
        """arwiz profile runs on simple_loop.py fixture."""
        result = subprocess.run(
            [
                "uv",
                "run",
                "arwiz",
                "profile",
                str(FIXTURES / "simple_loop.py"),
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        assert "profile_id" in result.stdout

    @pytest.mark.slow
    def test_cli_optimize(self) -> None:
        """arwiz optimize runs with template strategy."""
        result = subprocess.run(
            [
                "uv",
                "run",
                "arwiz",
                "optimize",
                str(FIXTURES / "simple_loop.py"),
                "--function",
                "compute_sum",
                "--strategy",
                "template",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0

    @pytest.mark.slow
    def test_cli_coverage(self) -> None:
        """arwiz coverage runs on branching.py fixture."""
        result = subprocess.run(
            [
                "uv",
                "run",
                "arwiz",
                "coverage",
                str(FIXTURES / "branching.py"),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0

    @pytest.mark.slow
    def test_cli_report(self, tmp_path: Path) -> None:
        """arwiz report displays a saved profile JSON."""
        profile_data = {
            "profile_id": "smoke-test-001",
            "script_path": str(FIXTURES / "simple_loop.py"),
            "duration_ms": 10.5,
            "hotspots": [
                {
                    "function_name": "compute_sum",
                    "self_time_ms": 5.0,
                    "call_count": 1,
                    "file_path": str(FIXTURES / "simple_loop.py"),
                    "line_range": [10, 15],
                },
            ],
        }
        profile_file = tmp_path / "profile.json"
        profile_file.write_text(json.dumps(profile_data))

        result = subprocess.run(
            [
                "uv",
                "run",
                "arwiz",
                "report",
                str(profile_file),
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "smoke-test-001" in result.stdout


@pytest.mark.integration
class TestFastAPISmoke:
    """FastAPI smoke tests using TestClient."""

    def test_api_import(self) -> None:
        """arwiz.api imports successfully and exposes app."""
        from arwiz.api import app

        assert app is not None
        assert app.title == "arwiz"

    def test_health_endpoint(self) -> None:
        """GET /health returns 200 with expected payload."""
        from arwiz.api import app

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "0.1.0"

    @pytest.mark.slow
    def test_profile_endpoint(self) -> None:
        """POST /profile profiles a fixture script."""
        from arwiz.api import app

        client = TestClient(app)
        response = client.post(
            "/profile",
            json={
                "script_path": str(FIXTURES / "simple_loop.py"),
                "timeout": 30,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "profile_id" in data
        assert "hotspots" in data
        assert data["duration_ms"] > 0


@pytest.mark.integration
class TestStreamlitSmoke:
    """Streamlit smoke tests — import-only, no browser."""

    def test_streamlit_import(self) -> None:
        """arwiz.streamlit_ui imports successfully."""
        import arwiz.streamlit_ui  # noqa: F401


@pytest.mark.integration
class TestOrchestratorSmoke:
    """Orchestrator smoke tests."""

    def test_default_orchestrator_instantiation(self) -> None:
        """DefaultOrchestrator imports and instantiates."""
        from arwiz.orchestrator import DefaultOrchestrator

        orchestrator = DefaultOrchestrator()
        assert orchestrator is not None
        assert orchestrator.last_pipeline_state is None

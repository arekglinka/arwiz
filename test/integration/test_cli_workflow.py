"""Integration tests for full CLI workflow: profile → optimize."""

from importlib import import_module
from pathlib import Path

import pytest
from click.testing import CliRunner

SIMPLE_LOOP_PATH = Path(__file__).parent.parent / "fixtures" / "targets" / "simple_loop.py"


@pytest.mark.slow
def test_profile_cli_shows_hotspots() -> None:
    try:
        cli = import_module("arwiz.cli").cli
        runner = CliRunner()
        result = runner.invoke(cli, ["profile", str(SIMPLE_LOOP_PATH)])

        assert result.exit_code == 0
        assert "compute_sum" in result.output
        assert "ms" in result.output
    except Exception as exc:
        pytest.fail(f"profile workflow failed for {SIMPLE_LOOP_PATH}: {exc}")


@pytest.mark.slow
def test_optimize_cli_template_strategy() -> None:
    try:
        cli = import_module("arwiz.cli").cli
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "optimize",
                str(SIMPLE_LOOP_PATH),
                "--function",
                "compute_sum",
                "--strategy",
                "template",
            ],
        )

        assert result.exit_code == 0
        assert any(token in result.output.lower() for token in ("numpy", "vectorize", "optimized"))
    except Exception as exc:
        pytest.fail(f"optimize workflow failed for {SIMPLE_LOOP_PATH}: {exc}")


@pytest.mark.slow
def test_coverage_cli_shows_branch_info() -> None:
    try:
        cli = import_module("arwiz.cli").cli
        runner = CliRunner()
        result = runner.invoke(cli, ["coverage", str(SIMPLE_LOOP_PATH)])

        assert result.exit_code == 0
        assert "%" in result.output
    except Exception as exc:
        pytest.fail(f"coverage workflow failed for {SIMPLE_LOOP_PATH}: {exc}")

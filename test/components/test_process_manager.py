"""Tests for arwiz.process_manager component."""

import os
import tempfile
import time

from arwiz.process_manager import DefaultProcessManager, ProcessResult
from arwiz.process_manager.interface import ProcessManagerProtocol


def _write_script(tmp: str, content: str, suffix: str = ".py") -> str:
    """Write a script to tmpdir and return its path."""
    path = os.path.join(tmp, f"script_{os.getpid()}{suffix}")
    with open(path, "w") as f:
        f.write(content)
    return path


class TestProcessResult:
    """Test ProcessResult dataclass."""

    def test_defaults(self):
        result = ProcessResult(exit_code=0, stdout="out", stderr="err")
        assert result.exit_code == 0
        assert result.stdout == "out"
        assert result.stderr == "err"
        assert result.timed_out is False
        assert result.memory_exceeded is False
        assert result.duration_ms == 0.0
        assert result.pid is None

    def test_all_fields(self):
        result = ProcessResult(
            exit_code=1,
            stdout="",
            stderr="error",
            timed_out=True,
            memory_exceeded=True,
            duration_ms=1500.0,
            pid=1234,
        )
        assert result.exit_code == 1
        assert result.timed_out is True
        assert result.memory_exceeded is True
        assert result.duration_ms == 1500.0
        assert result.pid == 1234


class TestDefaultProcessManager:
    """Test DefaultProcessManager implementation."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.pm = DefaultProcessManager()

    def test_protocol_conformance(self):
        """DefaultProcessManager satisfies ProcessManagerProtocol."""
        assert isinstance(self.pm, ProcessManagerProtocol)

    def test_run_script_successfully(self):
        """Run a simple print script, verify exit code 0, stdout captured."""
        script = _write_script(self.tmpdir, 'import sys; print("hello"); sys.exit(0)')
        result = self.pm.run_script(script)
        assert result.exit_code == 0
        assert "hello" in result.stdout
        assert result.timed_out is False
        assert result.memory_exceeded is False
        assert result.duration_ms > 0
        assert result.pid is not None

    def test_run_script_with_args(self):
        """Run script with CLI arguments."""
        script = _write_script(self.tmpdir, "import sys; print(' '.join(sys.argv[1:]))")
        result = self.pm.run_script(script, args=["foo", "bar", "baz"])
        assert result.exit_code == 0
        assert "foo bar baz" in result.stdout

    def test_run_script_timeout(self):
        """Run an infinite loop script with 2s timeout, verify timed_out=True."""
        script = _write_script(self.tmpdir, "import time; time.sleep(100)")
        result = self.pm.run_script(script, timeout_seconds=2)
        assert result.timed_out is True
        assert result.exit_code != 0

    def test_run_script_failure(self):
        """Run a script that exits with error, verify exit code != 0."""
        script = _write_script(self.tmpdir, "import sys; sys.exit(42)")
        result = self.pm.run_script(script)
        assert result.exit_code == 42

    def test_run_script_stderr_captured(self):
        """Verify stderr is captured."""
        script = _write_script(self.tmpdir, 'import sys; sys.stderr.write("oops\\n")')
        result = self.pm.run_script(script)
        assert result.exit_code == 0
        assert "oops" in result.stderr

    def test_kill_process(self):
        """Start a long-running script, kill it, verify it's dead."""
        script = _write_script(self.tmpdir, "import time; time.sleep(100)")
        # Use Popen directly to get the pid before communicate blocks
        import subprocess

        proc = subprocess.Popen(
            ["python", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # Wait briefly for process to start
        time.sleep(0.2)
        assert proc.poll() is None, "Process should be running"
        self.pm.kill_process(proc.pid)
        time.sleep(0.2)
        assert proc.poll() is not None, "Process should be dead after kill"

    def test_get_memory_usage(self):
        """Get memory of current process."""
        mem = self.pm.get_memory_usage_mb(os.getpid())
        assert mem > 0
        assert isinstance(mem, float)


class TestMemoryLimit:
    """Test memory limit enforcement."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.pm = DefaultProcessManager()

    def test_run_script_with_memory_limit(self):
        """Run a script that allocates memory beyond limit."""
        # Allocate 100MB, limit to 50MB
        script = _write_script(
            self.tmpdir,
            "buf = bytearray(100 * 1024 * 1024)",
        )
        result = self.pm.run_script(script, memory_limit_mb=50)
        # On Linux with RLIMIT_AS, the process should be killed
        # On other systems, psutil monitoring should catch it
        assert result.exit_code != 0 or result.memory_exceeded is True

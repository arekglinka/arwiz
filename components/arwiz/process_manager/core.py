"""Process execution with timeout and memory limits."""

from __future__ import annotations

import resource
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProcessResult:
    """Result of a subprocess execution."""

    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
    memory_exceeded: bool = False
    duration_ms: float = 0.0
    pid: int | None = None


class DefaultProcessManager:
    """Manages subprocess execution with timeout and memory constraints."""

    def run_script(
        self,
        script_path: Path | str,
        args: list[str] | None = None,
        timeout_seconds: int = 300,
        memory_limit_mb: int | None = None,
    ) -> ProcessResult:
        """Run a script as a subprocess.

        Args:
            script_path: Path to the script to execute.
            args: Additional CLI arguments to pass.
            timeout_seconds: Maximum execution time in seconds.
            memory_limit_mb: Memory limit in MB (uses RLIMIT_AS on Unix).

        Returns:
            ProcessResult with exit code, stdout, stderr, and metadata.
        """
        cmd = [sys.executable, str(script_path)]
        if args:
            cmd.extend(args)

        preexec_fn = None
        if memory_limit_mb is not None and sys.platform != "win32":
            limit_bytes = memory_limit_mb * 1024 * 1024

            def _set_memory_limit() -> None:
                resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))

            preexec_fn = _set_memory_limit

        start = time.perf_counter()
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=preexec_fn,
        )

        timed_out = False
        memory_exceeded = False
        exit_code = 0
        stdout = ""
        stderr = ""

        try:
            stdout, stderr = proc.communicate(timeout=timeout_seconds)
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.kill()
            stdout, stderr = proc.communicate()
            exit_code = proc.returncode

        # Negative exit_code = killed by signal (e.g. SIGKILL from RLIMIT_AS)
        if not timed_out and memory_limit_mb is not None and exit_code < 0:
            memory_exceeded = True

        if not timed_out and not memory_exceeded and memory_limit_mb is not None:
            try:
                import psutil

                try:
                    mem_usage = psutil.Process(proc.pid).memory_info().rss / 1024 / 1024
                    if mem_usage > memory_limit_mb:
                        memory_exceeded = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            except ImportError:
                pass

        elapsed = (time.perf_counter() - start) * 1000

        return ProcessResult(
            exit_code=exit_code,
            stdout=stdout or "",
            stderr=stderr or "",
            timed_out=timed_out,
            memory_exceeded=memory_exceeded,
            duration_ms=elapsed,
            pid=proc.pid,
        )

    def kill_process(self, pid: int) -> None:
        """Kill a process by PID.

        Sends SIGTERM first, then SIGKILL after a grace period.

        Args:
            pid: Process ID to kill.
        """
        import psutil

        try:
            proc = psutil.Process(pid)
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except psutil.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
        except psutil.NoSuchProcess:
            pass

    def get_memory_usage_mb(self, pid: int) -> float:
        """Get memory usage of a process in MB.

        Args:
            pid: Process ID to query.

        Returns:
            Memory usage in megabytes.
        """
        import psutil

        proc = psutil.Process(pid)
        return proc.memory_info().rss / 1024 / 1024

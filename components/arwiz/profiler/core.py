from __future__ import annotations

import pstats
import tempfile
import textwrap
from pathlib import Path

from ..foundation import ArwizConfig, ProfileResult, ProfilingConfig
from ..process_manager import DefaultProcessManager
from .parsers import parse_pstats


class DefaultProfiler:
    def __init__(self, process_manager: DefaultProcessManager | None = None) -> None:
        self._process_manager = process_manager or DefaultProcessManager()

    def profile_script(
        self,
        script_path: Path | str,
        args: list[str] | None = None,
        config: ProfilingConfig | ArwizConfig | None = None,
    ) -> ProfileResult:
        if isinstance(config, ArwizConfig):
            cfg = ProfilingConfig()
            timeout_seconds = config.timeout_seconds
            memory_limit_mb = config.memory_limit_mb
        else:
            cfg = config or ProfilingConfig()
            timeout_seconds = 300
            memory_limit_mb = None

        target_script = Path(script_path).resolve()
        cli_args = args or []

        with tempfile.TemporaryDirectory(prefix="arwiz_prof_") as tmpdir:
            tmp_path = Path(tmpdir)
            stats_path = tmp_path / "profile.pstats"
            wrapper_path = tmp_path / "profile_wrapper.py"

            wrapper_code = textwrap.dedent(
                """
                import cProfile
                import runpy
                import sys

                def _main() -> None:
                    script = sys.argv[1]
                    stats_out = sys.argv[2]
                    argv = sys.argv[3:]
                    profiler = cProfile.Profile()
                    sys.argv = [script, *argv]
                    profiler.enable()
                    try:
                        runpy.run_path(script, run_name="__main__")
                    finally:
                        profiler.disable()
                        profiler.dump_stats(stats_out)

                if __name__ == "__main__":
                    _main()
                """
            )
            wrapper_path.write_text(wrapper_code, encoding="utf-8")

            run_args = [str(target_script), str(stats_path), *cli_args]

            for _ in range(max(cfg.warmup_runs, 0)):
                self._process_manager.run_script(
                    script_path=wrapper_path,
                    args=run_args,
                    timeout_seconds=timeout_seconds,
                    memory_limit_mb=memory_limit_mb,
                )

            process_result = self._process_manager.run_script(
                script_path=wrapper_path,
                args=run_args,
                timeout_seconds=timeout_seconds,
                memory_limit_mb=memory_limit_mb,
            )

            if process_result.exit_code != 0 or not stats_path.exists():
                return ProfileResult(
                    script_path=str(target_script),
                    duration_ms=max(process_result.duration_ms, 0.0),
                    call_tree=None,
                    hotspots=[],
                )

            stats = pstats.Stats(str(stats_path))
            parsed = parse_pstats(stats, str(target_script))
            parsed.duration_ms = max(process_result.duration_ms, parsed.duration_ms)
            return parsed

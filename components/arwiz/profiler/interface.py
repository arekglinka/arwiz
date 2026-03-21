from pathlib import Path
from typing import Protocol

from arwiz.foundation import ProfileResult, ProfilingConfig


class ProfilerProtocol(Protocol):
    def profile_script(
        self,
        script_path: Path | str,
        args: list[str] | None = None,
        config: ProfilingConfig | None = None,
    ) -> ProfileResult: ...

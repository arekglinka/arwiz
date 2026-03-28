from __future__ import annotations

from importlib import import_module
from typing import Any


def _foundation():
    return import_module("arwiz.foundation")


class DummyConfigLoader:
    def load_config(self, _config_path=None):  # noqa: ANN001
        return _foundation().ArwizConfig()


class DummyProfiler:
    def profile_script(self, script_path, args=None, config=None):  # noqa: ANN001
        duration_ms = 10.0 + (0.0 * len(args or []))
        if config is not None:
            duration_ms += 0.0
        return _foundation().ProfileResult(script_path=str(script_path), duration_ms=duration_ms)


class DummyHotspotDetector:
    def __init__(self, hotspots: list[Any]) -> None:
        self.hotspots = hotspots

    def detect_hotspots(self, _profile_result, _threshold_pct=5.0):  # noqa: ANN001
        return list(self.hotspots)


class SequenceEquivalenceChecker:
    def __init__(self, outcomes: list[tuple[bool, str]]) -> None:
        self._outcomes = list(outcomes)

    def check_equivalence(self, *args, **kwargs):  # noqa: ANN002, ANN003, ARG002
        if self._outcomes:
            return self._outcomes.pop(0)
        return True, ""


class DummyEquivalenceChecker:
    def __init__(self, equivalent: bool = True, reason: str = "") -> None:
        self.equivalent = equivalent
        self.reason = reason

    def check_equivalence(self, *args, **kwargs):  # noqa: ANN002, ANN003, ARG002
        return self.equivalent, self.reason

from typing import Protocol

from arwiz.foundation import HotSpot, ProfileResult


class HotspotDetectorProtocol(Protocol):
    def detect_hotspots(
        self, profile_result: ProfileResult, threshold_pct: float = 5.0
    ) -> list[HotSpot]: ...
    def rank_by_impact(self, hotspots: list[HotSpot]) -> list[HotSpot]: ...

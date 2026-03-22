from ..foundation import HotSpot, ProfileResult


class DefaultHotspotDetector:
    def detect_hotspots(
        self, profile_result: ProfileResult, threshold_pct: float = 1.0
    ) -> list[HotSpot]:
        if profile_result.duration_ms <= 0 or not profile_result.hotspots:
            return []

        user_hotspots = [hs for hs in profile_result.hotspots if not hs.is_c_extension]
        if not user_hotspots:
            return []

        max_self_time = max(hs.self_time_ms for hs in user_hotspots)
        threshold_ms = (threshold_pct / 100.0) * max_self_time

        return [hs for hs in user_hotspots if hs.self_time_ms >= threshold_ms]

    def rank_by_impact(self, hotspots: list[HotSpot]) -> list[HotSpot]:
        return sorted(hotspots, key=lambda hs: hs.self_time_ms, reverse=True)

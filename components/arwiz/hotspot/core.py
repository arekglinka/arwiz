from arwiz.foundation import HotSpot, ProfileResult


class DefaultHotspotDetector:
    def detect_hotspots(
        self, profile_result: ProfileResult, threshold_pct: float = 5.0
    ) -> list[HotSpot]:
        if profile_result.duration_ms <= 0:
            return []

        threshold_ms = (threshold_pct / 100.0) * profile_result.duration_ms

        filtered: list[HotSpot] = []
        for hs in profile_result.hotspots:
            if hs.is_c_extension:
                continue
            if hs.cumulative_time_ms >= threshold_ms:
                filtered.append(hs)

        return filtered

    def rank_by_impact(self, hotspots: list[HotSpot]) -> list[HotSpot]:
        return sorted(hotspots, key=lambda hs: hs.potential_speedup, reverse=True)

"""Tests for arwiz.hotspot — Hotspot detection and ranking."""

import pytest
from arwiz.foundation import HotSpot, ProfileResult
from arwiz.hotspot.core import DefaultHotspotDetector


@pytest.fixture
def detector() -> DefaultHotspotDetector:
    return DefaultHotspotDetector()


@pytest.fixture
def profile_result() -> ProfileResult:
    return ProfileResult(
        script_path="/test.py",
        duration_ms=1000.0,
        hotspots=[
            HotSpot(
                function_name="slow_func",
                file_path="/test.py",
                line_range=(1, 10),
                cumulative_time_ms=500.0,
                self_time_ms=200.0,
                call_count=100,
                is_c_extension=False,
                potential_speedup=2.5,
            ),
            HotSpot(
                function_name="medium_func",
                file_path="/test.py",
                line_range=(20, 30),
                cumulative_time_ms=100.0,
                self_time_ms=50.0,
                call_count=50,
                is_c_extension=False,
                potential_speedup=1.5,
            ),
            HotSpot(
                function_name="tiny_func",
                file_path="/test.py",
                line_range=(40, 50),
                cumulative_time_ms=20.0,
                self_time_ms=20.0,
                call_count=10,
                is_c_extension=False,
                potential_speedup=0.5,
            ),
            HotSpot(
                function_name="c_ext_func",
                file_path="builtins",
                line_range=(0, 0),
                cumulative_time_ms=300.0,
                self_time_ms=300.0,
                call_count=1000,
                is_c_extension=True,
                potential_speedup=0.0,
            ),
        ],
    )


class TestDetectHotspots:
    def test_filters_by_threshold(
        self, detector: DefaultHotspotDetector, profile_result: ProfileResult
    ) -> None:
        detected = detector.detect_hotspots(profile_result, threshold_pct=5.0)
        names = [hs.function_name for hs in detected]
        assert "slow_func" in names
        assert "medium_func" in names
        assert "tiny_func" not in names

    def test_excludes_c_extensions(
        self, detector: DefaultHotspotDetector, profile_result: ProfileResult
    ) -> None:
        detected = detector.detect_hotspots(profile_result, threshold_pct=5.0)
        for hs in detected:
            assert hs.is_c_extension is False

    def test_higher_threshold_filters_more(
        self, detector: DefaultHotspotDetector, profile_result: ProfileResult
    ) -> None:
        detected_low = detector.detect_hotspots(profile_result, threshold_pct=5.0)
        detected_high = detector.detect_hotspots(profile_result, threshold_pct=40.0)
        assert len(detected_high) < len(detected_low)

    def test_empty_hotspots(self, detector: DefaultHotspotDetector) -> None:
        pr = ProfileResult(script_path="/test.py", duration_ms=100.0, hotspots=[])
        detected = detector.detect_hotspots(pr)
        assert detected == []

    def test_zero_duration_returns_empty(self, detector: DefaultHotspotDetector) -> None:
        hs = HotSpot(
            function_name="f",
            file_path="/t.py",
            line_range=(1, 2),
            cumulative_time_ms=10.0,
            self_time_ms=10.0,
        )
        pr = ProfileResult(script_path="/test.py", duration_ms=0.0, hotspots=[hs])
        detected = detector.detect_hotspots(pr)
        assert detected == []


class TestRankByImpact:
    def test_sorts_by_speedup_descending(
        self, detector: DefaultHotspotDetector, profile_result: ProfileResult
    ) -> None:
        detected = detector.detect_hotspots(profile_result, threshold_pct=5.0)
        ranked = detector.rank_by_impact(detected)
        for i in range(len(ranked) - 1):
            assert ranked[i].potential_speedup >= ranked[i + 1].potential_speedup

    def test_empty_list(self, detector: DefaultHotspotDetector) -> None:
        ranked = detector.rank_by_impact([])
        assert ranked == []

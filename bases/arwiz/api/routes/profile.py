from arwiz.api.models import ProfileRequest, ProfileResponse
from arwiz.hotspot import DefaultHotspotDetector
from arwiz.profiler import DefaultProfiler
from fastapi import APIRouter

router = APIRouter(tags=["profile"])


@router.post("/profile", response_model=ProfileResponse)
async def post_profile(req: ProfileRequest):
    profiler = DefaultProfiler()
    result = profiler.profile_script(req.script_path, args=req.args or None)

    detector = DefaultHotspotDetector()
    hotspots = detector.detect_hotspots(result)
    total_calls = sum(h.call_count for h in hotspots)

    return ProfileResponse(
        profile_id=result.profile_id,
        hotspots=[h.model_dump() for h in hotspots],
        duration_ms=result.duration_ms,
        total_calls=total_calls,
    )

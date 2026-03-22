from arwiz.api.models import CoverageRequest, CoverageResponse
from arwiz.coverage_tracer import DefaultCoverageTracer
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["coverage"])


@router.post("/coverage", response_model=CoverageResponse)
async def post_coverage(req: CoverageRequest):
    try:
        tracer = DefaultCoverageTracer()
        result = tracer.trace_branches(req.script_path, args=req.args or None)
        return CoverageResponse(
            total_branches=result.total_branches,
            covered_branches=result.covered_branches,
            coverage_percent=result.coverage_percent,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

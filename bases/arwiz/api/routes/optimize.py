from arwiz.api.models import OptimizeRequest, OptimizeResponse
from arwiz.orchestrator import DefaultOrchestrator
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["optimize"])


@router.post("/optimize", response_model=OptimizeResponse)
async def post_optimize(req: OptimizeRequest):
    try:
        orch = DefaultOrchestrator()
        result = orch.run_profile_optimize_pipeline(
            script_path=req.script_path,
            function_name=req.function_name,
            strategy=req.strategy,
        )
        return OptimizeResponse(**result.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

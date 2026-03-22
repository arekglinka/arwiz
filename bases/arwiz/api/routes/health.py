from arwiz.api.models import HealthResponse
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def get_health():
    try:
        return HealthResponse(status="ok", version="0.1.0")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

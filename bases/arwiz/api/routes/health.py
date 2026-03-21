from arwiz.api.models import HealthResponse
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def get_health():
    return HealthResponse(status="ok", version="0.1.0")

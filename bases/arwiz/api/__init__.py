# Brick: "bases/arwiz/api" = "arwiz/api"

from arwiz.api.routes.coverage import router as coverage_router
from arwiz.api.routes.health import router as health_router
from arwiz.api.routes.optimize import router as optimize_router
from arwiz.api.routes.profile import router as profile_router
from fastapi import FastAPI

app = FastAPI(
    title="arwiz",
    version="0.1.0",
    description="Python profiling and optimization API",
)

app.include_router(profile_router)
app.include_router(optimize_router)
app.include_router(coverage_router)
app.include_router(health_router)

__all__ = [
    "app",
    "profile_router",
    "optimize_router",
    "coverage_router",
    "health_router",
]

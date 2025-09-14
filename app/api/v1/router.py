"""
API v1 Router

Combines all v1 API endpoints and configures routing.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import analyze, status

# Create main v1 router
router = APIRouter(prefix="/api/v1", tags=["api-v1"])

# Include endpoint routers
router.include_router(
    analyze.router,
    prefix="",
    tags=["analysis"],
)

router.include_router(
    status.router,
    prefix="",
    tags=["status"],
)

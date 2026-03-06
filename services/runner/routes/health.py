"""
Health check endpoint.
"""

from fastapi import APIRouter

from ..schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """
    Health check endpoint.

    Returns the service status and version.
    """
    return HealthResponse(status="healthy", version="1.0.0")

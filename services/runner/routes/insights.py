"""
Insights API endpoint for standalone note generation.
"""

import json
import os
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Add core module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.insights import generate_insights_standalone
from core import AuthError, ProductboardError

from ..middleware.auth import verify_auth

router = APIRouter()


class GenerateInsightsRequest(BaseModel):
    """Request body for generating insights."""

    company: str
    website: str
    token: str
    count: int = 10


@router.post(
    "/insights",
    tags=["insights"],
)
async def generate_insights(
    request: GenerateInsightsRequest,
    _auth: str = Depends(verify_auth),
):
    """
    Generate customer feedback notes with streaming progress.

    Returns Server-Sent Events (SSE) with progress updates and final result.
    """

    def generate_events():
        try:
            for event in generate_insights_standalone(
                token=request.token,
                company=request.company,
                website=request.website,
                count=request.count,
            ):
                if event["type"] == "progress":
                    data = {
                        "current": event["current"],
                        "total": event["total"],
                        "note": event.get("note"),
                        "company": event.get("company"),
                        "phase": event.get("phase"),
                    }
                    yield f"event: progress\ndata: {json.dumps(data)}\n\n"
                elif event["type"] == "complete":
                    data = {
                        "status": "success",
                        "created": event["created"],
                        "failed": event.get("failed", 0),
                    }
                    yield f"event: complete\ndata: {json.dumps(data)}\n\n"
                elif event["type"] == "error":
                    data = {"message": event["message"]}
                    yield f"event: error\ndata: {json.dumps(data)}\n\n"

        except AuthError as e:
            error_data = {"message": str(e)}
            yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
        except ProductboardError as e:
            error_data = {"message": str(e)}
            yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
        except Exception as e:
            error_data = {"message": str(e)}
            yield f"event: error\ndata: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )

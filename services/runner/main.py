"""
Productboard Demo Generator - FastAPI Runner Service

This service exposes the core POC functionality via HTTP API.
"""

import os
import sys
from pathlib import Path

# Force unbuffered stdout for Railway logs
sys.stdout.reconfigure(line_buffering=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add core module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .routes import health, mappings, products, run, insights

# Create FastAPI app
app = FastAPI(
    title="Productboard Demo Generator API",
    description="API for generating and applying Productboard demo environments",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
# In production, this should be more restrictive
cors_origins = os.environ.get("CORS_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(products.router, prefix="/api", tags=["products"])
app.include_router(mappings.router, prefix="/api", tags=["mappings"])
app.include_router(run.router, prefix="/api", tags=["jobs"])
app.include_router(insights.router, prefix="/api", tags=["insights"])


@app.on_event("startup")
async def startup_event():
    """Log startup info."""
    print("=" * 60)
    print("Productboard Demo Generator API")
    print("=" * 60)

    # Check for required environment variables
    runner_secret = os.environ.get("RUNNER_SECRET")
    llm_provider = os.environ.get("LLM_PROVIDER", "gemini")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    if not runner_secret:
        print("WARNING: RUNNER_SECRET not set - authentication disabled")
    else:
        print("Authentication: enabled")

    if llm_provider == "gemini":
        if gemini_key:
            print(f"AI Generation: enabled (Gemini)")
        else:
            print("WARNING: GEMINI_API_KEY not set - using template fallback")
    else:
        if anthropic_key:
            print(f"AI Generation: enabled (Anthropic)")
        else:
            print("WARNING: ANTHROPIC_API_KEY not set - using template fallback")

    print("=" * 60)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=os.environ.get("ENV", "development") == "development",
    )

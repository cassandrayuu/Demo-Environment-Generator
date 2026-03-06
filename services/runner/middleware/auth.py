"""
Authentication middleware.

Validates shared secret for worker-to-runner communication.
"""

import os
from typing import Optional

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Get shared secret from environment
RUNNER_SECRET = os.environ.get("RUNNER_SECRET", "")


class SharedSecretAuth(HTTPBearer):
    """
    Authentication using shared secret.

    The Cloudflare Worker sends a Bearer token that must match RUNNER_SECRET.
    """

    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        # Skip auth in development if no secret is set
        if not RUNNER_SECRET:
            return None

        credentials = await super().__call__(request)

        if credentials:
            if credentials.credentials != RUNNER_SECRET:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                )
            return credentials

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
        )


# Create auth dependency
auth_scheme = SharedSecretAuth(auto_error=True)


async def verify_auth(request: Request) -> Optional[str]:
    """
    Verify authentication.

    Returns the verified secret or None if auth is disabled.
    """
    if not RUNNER_SECRET:
        # Auth disabled in development
        return None

    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format",
        )

    token = auth_header[7:]  # Remove "Bearer " prefix
    if token != RUNNER_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    return token

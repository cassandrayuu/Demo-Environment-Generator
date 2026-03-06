"""
Products endpoint.
"""

import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status

# Add core module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core import AuthError, ProductboardError, analyze_space, list_products

from ..middleware.auth import verify_auth
from ..schemas import (
    AnalyzeRecommendations,
    AnalyzeRequest,
    AnalyzeResponse,
    ErrorResponse,
    ListProductsRequest,
    ListProductsResponse,
    ProductInfoResponse,
)

router = APIRouter()


@router.post(
    "/products/list",
    response_model=ListProductsResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid token"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    tags=["products"],
)
async def list_pb_products(
    request: ListProductsRequest,
    _auth: str = Depends(verify_auth),
):
    """
    List products in a Productboard space.

    Returns all products with their component and feature counts.
    """
    try:
        products = list_products(request.token)

        return ListProductsResponse(
            products=[
                ProductInfoResponse(
                    id=p.id,
                    name=p.name,
                    componentCount=p.component_count,
                    featureCount=p.feature_count,
                    eligible=p.eligible,
                    ineligibleReason=p.ineligible_reason,
                )
                for p in products
            ]
        )

    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED if "Invalid" in str(e) else status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ProductboardError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid token"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    tags=["products"],
)
async def analyze_pb_space(
    request: AnalyzeRequest,
    _auth: str = Depends(verify_auth),
):
    """
    Analyze a Productboard space.

    Returns products with eligibility info and recommendations for auto-selection.
    Does NOT mutate anything - only reads data.
    """
    try:
        result = analyze_space(request.token)

        return AnalyzeResponse(
            products=[
                ProductInfoResponse(
                    id=p.id,
                    name=p.name,
                    componentCount=p.component_count,
                    featureCount=p.feature_count,
                    eligible=p.eligible,
                    ineligibleReason=p.ineligible_reason,
                )
                for p in result.products
            ],
            warnings=result.warnings,
            recommendations=AnalyzeRecommendations(
                autoSelectProductIds=result.auto_select_product_ids,
            ),
        )

    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED if "Invalid" in str(e) else status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ProductboardError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

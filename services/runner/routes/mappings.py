"""
Mappings generation endpoint.
"""

import os
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status

# Add core module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core import GenerationError, generate_mappings, generate_mappings_from_template

from ..middleware.auth import verify_auth
from ..schemas import (
    ComponentMappingSchema,
    ErrorResponse,
    FeatureMappingSchema,
    GenerateMappingsRequest,
    GenerateMappingsResponse,
    InitiativeMappingSchema,
    KeyResultMappingSchema,
    ObjectiveMappingSchema,
    ProductHierarchyMappingSchema,
    ProductMappingSchema,
    StrategyMappingSchema,
)

router = APIRouter()


def _convert_product_mapping(mapping) -> ProductMappingSchema:
    """Convert core ProductMapping to schema."""
    return ProductMappingSchema(
        customer=mapping.customer,
        hierarchy=[
            ProductHierarchyMappingSchema(
                position=p.position,
                newName=p.new_name,
                components=[
                    ComponentMappingSchema(
                        position=c.position,
                        newName=c.new_name,
                        features=[
                            FeatureMappingSchema(position=f.position, newName=f.new_name)
                            for f in c.features
                        ],
                    )
                    for c in p.components
                ],
            )
            for p in mapping.hierarchy
        ],
    )


def _convert_strategy_mapping(mapping) -> StrategyMappingSchema:
    """Convert core StrategyMapping to schema."""
    return StrategyMappingSchema(
        customer=mapping.customer,
        objectives=[
            ObjectiveMappingSchema(
                position=o.position,
                newName=o.new_name,
                keyResults=[
                    KeyResultMappingSchema(position=kr.position, newName=kr.new_name)
                    for kr in o.key_results
                ],
            )
            for o in mapping.objectives
        ],
        initiatives=[
            InitiativeMappingSchema(position=i.position, newName=i.new_name)
            for i in mapping.initiatives
        ],
    )


@router.post(
    "/mappings/generate",
    response_model=GenerateMappingsResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Generation failed"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    tags=["mappings"],
)
async def generate_pb_mappings(
    request: GenerateMappingsRequest,
    _auth: str = Depends(verify_auth),
):
    """
    Generate mapping files for a company.

    Uses AI to generate realistic product, strategy, and feature mappings
    based on the company name and website.
    """
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")

    try:
        if anthropic_api_key:
            mappings = generate_mappings(
                company=request.company,
                website=request.website,
                anthropic_api_key=anthropic_api_key,
            )
        else:
            # Fallback to template if no API key
            mappings = generate_mappings_from_template(request.company)

        return GenerateMappingsResponse(
            productMapping=_convert_product_mapping(mappings.product_mapping),
            strategyMapping=_convert_strategy_mapping(mappings.strategy_mapping),
            features=mappings.features_list,
        )

    except GenerationError as e:
        # Try template fallback
        try:
            mappings = generate_mappings_from_template(request.company)
            return GenerateMappingsResponse(
                productMapping=_convert_product_mapping(mappings.product_mapping),
                strategyMapping=_convert_strategy_mapping(mappings.strategy_mapping),
                features=mappings.features_list,
            )
        except Exception as e2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Generation failed: {e2}",
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

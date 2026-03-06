"""
Run and validate endpoints.
"""

import json
import os
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

# Add core module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core import (
    AuthError,
    ComponentMapping,
    FeatureMapping,
    FlexibleOptions,
    GeneratedMappings,
    InitiativeMapping,
    KeyResultMapping,
    ObjectiveMapping,
    ProductboardError,
    ProductHierarchyMapping,
    ProductMapping,
    StrategyMapping,
    preflight_check,
    run_poc_streaming,
)

from ..middleware.auth import verify_auth
from ..schemas import (
    ErrorResponse,
    JobResultResponse,
    MappingsSchema,
    RunJobRequest,
    SelectedProductResponse,
    StepResultResponse,
    StepStatus,
    ValidateRequest,
    ValidationErrorResponse,
    ValidationResultResponse,
)

router = APIRouter()


def _convert_mappings_to_core(mappings: MappingsSchema) -> GeneratedMappings:
    """Convert schema mappings to core GeneratedMappings."""
    # Convert product mapping
    hierarchy = []
    for p in mappings.productMapping.hierarchy:
        components = []
        for c in p.components:
            features = [
                FeatureMapping(position=f.position, new_name=f.newName)
                for f in c.features
            ]
            components.append(
                ComponentMapping(position=c.position, new_name=c.newName, features=features)
            )
        hierarchy.append(
            ProductHierarchyMapping(
                position=p.position, new_name=p.newName, components=components
            )
        )
    product_mapping = ProductMapping(
        customer=mappings.productMapping.customer, hierarchy=hierarchy
    )

    # Convert strategy mapping
    objectives = []
    for o in mappings.strategyMapping.objectives:
        key_results = [
            KeyResultMapping(position=kr.position, new_name=kr.newName)
            for kr in o.keyResults
        ]
        objectives.append(
            ObjectiveMapping(
                position=o.position, new_name=o.newName, key_results=key_results
            )
        )
    initiatives = [
        InitiativeMapping(position=i.position, new_name=i.newName)
        for i in mappings.strategyMapping.initiatives
    ]
    strategy_mapping = StrategyMapping(
        customer=mappings.strategyMapping.customer,
        objectives=objectives,
        initiatives=initiatives,
    )

    return GeneratedMappings(
        product_mapping=product_mapping,
        strategy_mapping=strategy_mapping,
        features_list=mappings.features,
    )


@router.post(
    "/run",
    responses={
        400: {"model": ErrorResponse, "description": "Validation failed"},
        401: {"model": ErrorResponse, "description": "Invalid token"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    tags=["jobs"],
)
async def run_job(
    request: RunJobRequest,
    _auth: str = Depends(verify_auth),
):
    """
    Run a POC job with streaming progress updates.

    Uses flexible generation that adapts to the actual structure of selected products.
    Returns Server-Sent Events (SSE) with step completions and final result.
    """
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")

    # Convert mappings if provided
    mappings = None
    if request.mappings:
        mappings = _convert_mappings_to_core(request.mappings)

    # Convert options if provided
    options = None
    if request.options:
        options = FlexibleOptions(
            max_components_per_product=request.options.maxComponentsPerProduct,
            max_features_per_component=request.options.maxFeaturesPerComponent,
        )

    def generate_events():
        try:
            for event in run_poc_streaming(
                company=request.company,
                website=request.website,
                token=request.token,
                selected_product_ids=request.selectedProductIds,
                mode=request.mode.value,
                mappings=mappings,
                anthropic_api_key=anthropic_api_key,
                options=options,
            ):
                if event["type"] == "step":
                    step = event["step"]
                    data = {
                        "type": "step",
                        "step": {
                            "name": step.name,
                            "status": step.status.value,
                            "summary": step.summary,
                            "error": step.error,
                        },
                    }
                elif event["type"] == "complete":
                    result = event["result"]
                    # Determine status from errors
                    job_status = "failed" if result.errors else "completed"
                    data = {
                        "type": "complete",
                        "result": {
                            "jobId": result.job_id,
                            "status": job_status,
                            "mode": result.mode,
                            "company": result.company,
                            "website": result.website,
                            "selectedProducts": [
                                {"id": p.id, "name": p.name}
                                for p in result.selected_products
                            ],
                            "steps": [
                                {
                                    "name": s.name,
                                    "status": s.status.value,
                                    "summary": s.summary,
                                    "logs": s.logs,
                                    "error": s.error,
                                }
                                for s in result.steps
                            ],
                            "warnings": result.warnings,
                            "errors": result.errors,
                            "completedAt": result.completed_at,
                        },
                    }
                else:
                    continue

                yield f"data: {json.dumps(data)}\n\n"

        except AuthError as e:
            error_data = {"type": "error", "error": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"
        except Exception as e:
            error_data = {"type": "error", "error": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post(
    "/validate",
    response_model=ValidationResultResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid token"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    tags=["validation"],
)
async def validate_preflight(
    request: ValidateRequest,
    _auth: str = Depends(verify_auth),
):
    """
    Perform preflight validation.

    Validates:
    - Token is valid
    - Selected products exist
    - Each selected product has >= 3 components
    - Mappings are valid (if provided)
    """
    # Convert mappings if provided
    product_mapping = None
    strategy_mapping = None
    features = None

    if request.mappings:
        core_mappings = _convert_mappings_to_core(request.mappings)
        product_mapping = core_mappings.product_mapping
        strategy_mapping = core_mappings.strategy_mapping
        features = core_mappings.features_list

    try:
        result = preflight_check(
            token=request.token,
            selected_product_ids=request.selectedProductIds,
            product_mapping=product_mapping,
            strategy_mapping=strategy_mapping,
            features=features,
        )

        return ValidationResultResponse(
            valid=result.valid,
            errors=[
                ValidationErrorResponse(field=e.field, message=e.message)
                for e in result.errors
            ],
            warnings=result.warnings,
        )

    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED
            if "Invalid" in str(e)
            else status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

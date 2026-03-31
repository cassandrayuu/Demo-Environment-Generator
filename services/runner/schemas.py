"""
Pydantic schemas for API request/response models.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==================== Enums ====================


class JobMode(str, Enum):
    DRY_RUN = "dry-run"
    APPLY = "apply"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"


# ==================== Request Models ====================


class ListProductsRequest(BaseModel):
    """Request to list products in a Productboard space."""

    token: str = Field(..., description="Productboard API token")


class AnalyzeRequest(BaseModel):
    """Request to analyze a Productboard space."""

    token: str = Field(..., description="Productboard API token")
    company: str = Field(..., min_length=1, description="Company name")
    website: str = Field(..., description="Company website URL")


class GenerateMappingsRequest(BaseModel):
    """Request to generate mapping files."""

    company: str = Field(..., min_length=1, description="Company name")
    website: str = Field(..., description="Company website URL")


class FeatureMappingSchema(BaseModel):
    position: int
    newName: str


class ComponentMappingSchema(BaseModel):
    position: int
    newName: str
    features: List[FeatureMappingSchema]


class ProductHierarchyMappingSchema(BaseModel):
    position: int
    newName: str
    components: List[ComponentMappingSchema]


class ProductMappingSchema(BaseModel):
    customer: str
    hierarchy: List[ProductHierarchyMappingSchema]


class KeyResultMappingSchema(BaseModel):
    position: int
    newName: str


class ObjectiveMappingSchema(BaseModel):
    position: int
    newName: str
    keyResults: List[KeyResultMappingSchema]


class InitiativeMappingSchema(BaseModel):
    position: int
    newName: str


class StrategyMappingSchema(BaseModel):
    customer: str
    objectives: List[ObjectiveMappingSchema]
    initiatives: List[InitiativeMappingSchema]


class MappingsSchema(BaseModel):
    """Complete mappings for a POC run."""

    productMapping: ProductMappingSchema
    strategyMapping: StrategyMappingSchema
    features: List[str]


class FlexibleOptionsSchema(BaseModel):
    """Options for flexible hierarchy generation."""

    maxComponentsPerProduct: int = Field(default=10, ge=1, le=50)
    maxFeaturesPerComponent: int = Field(default=20, ge=1, le=100)


class RunJobRequest(BaseModel):
    """Request to run a POC job."""

    company: str = Field(..., min_length=1, description="Company name")
    website: str = Field(..., description="Company website URL")
    token: str = Field(..., description="Productboard API token")
    selectedProductIds: List[str] = Field(
        ..., min_length=1, max_length=2, description="IDs of 1-2 products to rename"
    )
    mode: JobMode = Field(default=JobMode.APPLY, description="Run mode (apply by default)")
    includeStrategy: bool = Field(
        default=True, description="Whether to rename strategy items (objectives/initiatives)"
    )
    mappings: Optional[MappingsSchema] = Field(
        default=None, description="Pre-generated mappings (generated if not provided)"
    )
    options: Optional[FlexibleOptionsSchema] = Field(
        default=None, description="Options for flexible generation caps"
    )


class ValidateRequest(BaseModel):
    """Request for preflight validation."""

    token: str = Field(..., description="Productboard API token")
    selectedProductIds: List[str] = Field(
        ..., min_length=1, max_length=2, description="IDs of 1-2 products to rename"
    )
    mappings: Optional[MappingsSchema] = Field(
        default=None, description="Mappings to validate"
    )


# ==================== Response Models ====================


class ProductInfoResponse(BaseModel):
    """Information about a single product."""

    id: str
    name: str
    componentCount: int
    featureCount: int = 0
    eligible: bool = True
    ineligibleReason: Optional[str] = None


class ListProductsResponse(BaseModel):
    """Response containing list of products."""

    products: List[ProductInfoResponse]


class AnalyzeRecommendations(BaseModel):
    """Recommendations from analysis."""

    autoSelectProductIds: List[str] = []


class AnalyzeResponse(BaseModel):
    """Response from analyzing a Productboard space."""

    products: List[ProductInfoResponse]
    warnings: List[str] = []
    recommendations: AnalyzeRecommendations


class GenerateMappingsResponse(BaseModel):
    """Response containing generated mappings."""

    productMapping: ProductMappingSchema
    strategyMapping: StrategyMappingSchema
    features: List[str]


class StepResultResponse(BaseModel):
    """Result of a single job step."""

    name: str
    status: StepStatus
    summary: Dict[str, Any] = {}
    logs: List[str] = []
    error: Optional[str] = None


class SelectedProductResponse(BaseModel):
    """A selected product."""

    id: str
    name: str


class JobResultResponse(BaseModel):
    """Complete job result."""

    jobId: str
    mode: str
    company: str
    website: str
    selectedProducts: List[SelectedProductResponse]
    steps: List[StepResultResponse]
    warnings: List[str] = []
    errors: List[str] = []
    completedAt: Optional[str] = None


class ValidationErrorResponse(BaseModel):
    """A single validation error."""

    field: str
    message: str


class ValidationResultResponse(BaseModel):
    """Validation result."""

    valid: bool
    errors: List[ValidationErrorResponse] = []
    warnings: List[str] = []


class ErrorResponse(BaseModel):
    """Generic error response."""

    error: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str = "1.0.0"

"""
Productboard Demo Environment Generator - Core Module

This package contains the core business logic for the Productboard demo setup tool.
"""

# Models
from .models import (
    AnalyzeResult,
    ComponentMapping,
    ComponentStructure,
    FeatureMapping,
    FlexibleOptions,
    InitiativeMapping,
    JobResult,
    KeyResultMapping,
    ObjectiveMapping,
    ProductHierarchyMapping,
    ProductInfo,
    ProductMapping,
    ProductStructure,
    RenamePlan,
    SelectedProduct,
    StepResult,
    StepStatus,
    StrategyMapping,
    ValidationError,
    ValidationResult,
    DEFAULT_MAX_PRODUCTS,
    DEFAULT_MAX_COMPONENTS_PER_PRODUCT,
    DEFAULT_MAX_FEATURES_PER_COMPONENT,
)

# Client
from .pb_client import (
    AuthError,
    NotFoundError,
    ProductboardClient,
    ProductboardError,
    RateLimitError,
    ServerError,
    ValidationError as PBValidationError,
    default_client,
)

# Generator
from .generator import (
    GeneratedMappings,
    GenerationError,
    create_rename_plan,
    generate_flexible_mappings,
    generate_flexible_mappings_from_template,
    generate_mappings,
    generate_mappings_from_template,
)

# Hierarchy
from .hierarchy import (
    HierarchyEntity,
    ProductHierarchy,
    analyze_space,
    build_hierarchy,
    get_product_structure,
    list_products,
    rename_hierarchy,
)

# Strategy
from .strategy import (
    StrategyEntity,
    StrategyHierarchy,
    build_strategy_hierarchy,
    rename_strategy,
)

# Insights
from .insights import (
    GeneratedNote,
    generate_insights,
    generate_notes,
)

# Validators
from .validators import (
    preflight_check,
    validate_features_list,
    validate_product_mapping,
    validate_strategy_mapping,
)

# Runner
from .runner import run_poc, run_poc_streaming

__all__ = [
    # Models
    "AnalyzeResult",
    "ComponentMapping",
    "ComponentStructure",
    "FeatureMapping",
    "FlexibleOptions",
    "InitiativeMapping",
    "JobResult",
    "KeyResultMapping",
    "ObjectiveMapping",
    "ProductHierarchyMapping",
    "ProductInfo",
    "ProductMapping",
    "ProductStructure",
    "RenamePlan",
    "SelectedProduct",
    "StepResult",
    "StepStatus",
    "StrategyMapping",
    "ValidationError",
    "ValidationResult",
    "DEFAULT_MAX_PRODUCTS",
    "DEFAULT_MAX_COMPONENTS_PER_PRODUCT",
    "DEFAULT_MAX_FEATURES_PER_COMPONENT",
    # Client
    "AuthError",
    "NotFoundError",
    "ProductboardClient",
    "ProductboardError",
    "RateLimitError",
    "ServerError",
    "PBValidationError",
    "default_client",
    # Generator
    "GeneratedMappings",
    "GenerationError",
    "create_rename_plan",
    "generate_flexible_mappings",
    "generate_flexible_mappings_from_template",
    "generate_mappings",
    "generate_mappings_from_template",
    # Hierarchy
    "HierarchyEntity",
    "ProductHierarchy",
    "analyze_space",
    "build_hierarchy",
    "get_product_structure",
    "list_products",
    "rename_hierarchy",
    # Strategy
    "StrategyEntity",
    "StrategyHierarchy",
    "build_strategy_hierarchy",
    "rename_strategy",
    # Insights
    "GeneratedNote",
    "generate_insights",
    "generate_notes",
    # Validators
    "preflight_check",
    "validate_features_list",
    "validate_product_mapping",
    "validate_strategy_mapping",
    # Runner
    "run_poc",
    "run_poc_streaming",
]

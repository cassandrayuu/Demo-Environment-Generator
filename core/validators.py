"""
Validation utilities.

Provides validation for mappings and preflight checks.
"""

from typing import List, Optional

from .hierarchy import list_products
from .models import (
    DEFAULT_MAX_PRODUCTS,
    FlexibleOptions,
    ProductMapping,
    StrategyMapping,
    ValidationError,
    ValidationResult,
)
from .pb_client import AuthError, ProductboardClient, ProductboardError, default_client

# Strategy constraints (still fixed for MVP)
REQUIRED_OBJECTIVES = 3
REQUIRED_KEY_RESULTS_PER_OBJECTIVE = 2
REQUIRED_INITIATIVES = 6
MIN_FEATURES_LIST = 10

# Minimum requirements for eligibility
MIN_COMPONENTS_FOR_ELIGIBILITY = 1  # Must have at least 1 component


def validate_product_mapping(
    mapping: ProductMapping, flexible: bool = False
) -> ValidationResult:
    """
    Validate that a product mapping meets requirements.

    If flexible=True, we only validate that mappings are well-formed,
    not that they match fixed counts.
    """
    errors: List[ValidationError] = []
    warnings: List[str] = []

    if not flexible:
        # Legacy validation: fixed counts
        if len(mapping.hierarchy) != DEFAULT_MAX_PRODUCTS:
            errors.append(
                ValidationError(
                    field="hierarchy",
                    message=f"Expected {DEFAULT_MAX_PRODUCTS} products, got {len(mapping.hierarchy)}",
                )
            )

    # Validate structure is well-formed
    for i, product in enumerate(mapping.hierarchy):
        product_path = f"hierarchy[{i}]"

        if not product.new_name:
            errors.append(
                ValidationError(
                    field=f"{product_path}.newName",
                    message=f"Product {i + 1} has no name",
                )
            )

        for j, component in enumerate(product.components):
            component_path = f"{product_path}.components[{j}]"

            if not component.new_name:
                errors.append(
                    ValidationError(
                        field=f"{component_path}.newName",
                        message=f"Component {j + 1} of product {i + 1} has no name",
                    )
                )

            for k, feature in enumerate(component.features):
                if not feature.new_name:
                    warnings.append(
                        f"Feature {k + 1} of component {j + 1} of product {i + 1} has no name"
                    )

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_strategy_mapping(mapping: StrategyMapping) -> ValidationResult:
    """
    Validate that a strategy mapping meets all requirements.

    Requirements:
    - Exactly 3 objectives
    - Exactly 2 key results per objective
    - Exactly 6 initiatives
    """
    errors: List[ValidationError] = []
    warnings: List[str] = []

    # Check objective count
    if len(mapping.objectives) != REQUIRED_OBJECTIVES:
        errors.append(
            ValidationError(
                field="objectives",
                message=f"Expected {REQUIRED_OBJECTIVES} objectives, got {len(mapping.objectives)}",
            )
        )

    # Check each objective
    for i, objective in enumerate(mapping.objectives):
        objective_path = f"objectives[{i}]"

        # Check key result count
        if len(objective.key_results) != REQUIRED_KEY_RESULTS_PER_OBJECTIVE:
            errors.append(
                ValidationError(
                    field=f"{objective_path}.keyResults",
                    message=f"Objective {i + 1} has {len(objective.key_results)} key results, expected {REQUIRED_KEY_RESULTS_PER_OBJECTIVE}",
                )
            )

    # Check initiative count
    if len(mapping.initiatives) != REQUIRED_INITIATIVES:
        errors.append(
            ValidationError(
                field="initiatives",
                message=f"Expected {REQUIRED_INITIATIVES} initiatives, got {len(mapping.initiatives)}",
            )
        )

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_features_list(features: List[str]) -> ValidationResult:
    """
    Validate that a features list meets requirements.

    Requirements:
    - At least 10 features
    """
    errors: List[ValidationError] = []
    warnings: List[str] = []

    if len(features) < MIN_FEATURES_LIST:
        errors.append(
            ValidationError(
                field="features",
                message=f"Expected at least {MIN_FEATURES_LIST} features, got {len(features)}",
            )
        )

    # Check for empty names
    empty_count = sum(1 for f in features if not f.strip())
    if empty_count > 0:
        warnings.append(f"{empty_count} feature names are empty")

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def preflight_check(
    token: str,
    selected_product_ids: List[str],
    product_mapping: Optional[ProductMapping] = None,
    strategy_mapping: Optional[StrategyMapping] = None,
    features: Optional[List[str]] = None,
    client: Optional[ProductboardClient] = None,
    flexible: bool = True,
) -> ValidationResult:
    """
    Perform preflight validation before running a POC.

    Checks:
    1. Token is valid
    2. Selected products exist (1-2 products allowed)
    3. Each selected product has at least 1 component
    4. Mappings are valid (if provided)

    Args:
        token: Productboard API token
        selected_product_ids: IDs of 1-2 products to rename
        product_mapping: Optional product mapping to validate
        strategy_mapping: Optional strategy mapping to validate
        features: Optional features list to validate
        client: Optional ProductboardClient instance
        flexible: If True, use flexible validation rules

    Returns:
        ValidationResult with any errors and warnings
    """
    client = client or default_client
    errors: List[ValidationError] = []
    warnings: List[str] = []

    # 1. Validate token
    try:
        client.validate_token(token)
    except AuthError as e:
        errors.append(ValidationError(field="token", message=str(e)))
        # Can't proceed without valid token
        return ValidationResult(valid=False, errors=errors, warnings=warnings)
    except ProductboardError as e:
        errors.append(ValidationError(field="token", message=f"Failed to validate token: {e}"))
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    # 2. Check product count (1-2 allowed)
    if len(selected_product_ids) < 1:
        errors.append(
            ValidationError(
                field="selectedProductIds",
                message="At least 1 product must be selected",
            )
        )
    elif len(selected_product_ids) > DEFAULT_MAX_PRODUCTS:
        errors.append(
            ValidationError(
                field="selectedProductIds",
                message=f"Maximum {DEFAULT_MAX_PRODUCTS} products allowed, got {len(selected_product_ids)}",
            )
        )

    # 3. Validate selected products exist and have at least 1 component
    try:
        products = list_products(token, client)
        products_by_id = {p.id: p for p in products}

        for i, product_id in enumerate(selected_product_ids):
            if product_id not in products_by_id:
                errors.append(
                    ValidationError(
                        field=f"selectedProductIds[{i}]",
                        message=f"Product with ID '{product_id}' not found in space",
                    )
                )
            else:
                product = products_by_id[product_id]
                if product.component_count < MIN_COMPONENTS_FOR_ELIGIBILITY:
                    errors.append(
                        ValidationError(
                            field=f"selectedProductIds[{i}]",
                            message=f"Product '{product.name}' has no components",
                        )
                    )

    except ProductboardError as e:
        errors.append(
            ValidationError(field="products", message=f"Failed to fetch products: {e}")
        )

    # 4. Validate mappings if provided
    if product_mapping:
        mapping_result = validate_product_mapping(product_mapping, flexible=flexible)
        errors.extend(mapping_result.errors)
        warnings.extend(mapping_result.warnings)

    if strategy_mapping:
        mapping_result = validate_strategy_mapping(strategy_mapping)
        errors.extend(mapping_result.errors)
        warnings.extend(mapping_result.warnings)

    if features:
        features_result = validate_features_list(features)
        errors.extend(features_result.errors)
        warnings.extend(features_result.warnings)

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)

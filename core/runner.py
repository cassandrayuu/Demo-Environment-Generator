"""
POC Runner - Orchestrates the complete demo setup.

Coordinates all steps:
1. Analyze structure of selected products
2. Generate mappings (AI-powered, matching actual structure)
3. Validate preflight
4. Rename product hierarchy
5. Rename strategy hierarchy
6. Generate user insights
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from .generator import (
    GeneratedMappings,
    GenerationError,
    create_rename_plan,
    generate_flexible_mappings,
    generate_flexible_mappings_from_template,
    generate_mappings,
    generate_mappings_from_template,
)
from .hierarchy import get_product_structure, list_products, rename_hierarchy
from .insights import generate_insights
from .models import (
    FlexibleOptions,
    JobResult,
    ProductMapping,
    RenamePlan,
    SelectedProduct,
    StepResult,
    StepStatus,
    StrategyMapping,
)
from .pb_client import ProductboardClient, default_client
from .strategy import rename_strategy
from .validators import preflight_check, validate_features_list, validate_product_mapping, validate_strategy_mapping


def run_poc(
    company: str,
    website: str,
    token: str,
    selected_product_ids: List[str],
    mode: str = "apply",  # Default to apply now
    mappings: Optional[GeneratedMappings] = None,
    anthropic_api_key: Optional[str] = None,
    client: Optional[ProductboardClient] = None,
    options: Optional[FlexibleOptions] = None,
) -> JobResult:
    """
    Run the complete POC setup.

    Uses flexible generation that adapts to the actual structure of selected products.

    Args:
        company: Company name
        website: Company website URL
        token: Productboard API token
        selected_product_ids: IDs of 1-2 products to rename
        mode: 'dry-run' or 'apply'
        mappings: Optional pre-generated mappings (generated if not provided)
        anthropic_api_key: Optional Anthropic API key for AI generation
        client: Optional ProductboardClient instance
        options: Optional FlexibleOptions for caps

    Returns:
        JobResult with complete execution details
    """
    client = client or default_client
    options = options or FlexibleOptions()
    apply = mode == "apply"
    job_id = str(uuid.uuid4())

    steps: List[StepResult] = []
    warnings: List[str] = []
    errors: List[str] = []

    # Get product info for selected products
    selected_products: List[SelectedProduct] = []
    try:
        products = list_products(token, client)
        products_by_id = {p.id: p for p in products}
        for pid in selected_product_ids:
            if pid in products_by_id:
                p = products_by_id[pid]
                selected_products.append(SelectedProduct(id=p.id, name=p.name))
    except Exception:
        # Will be caught in preflight
        pass

    # Step 0: Analyze structure (needed for flexible generation)
    structure = []
    if mappings is None:
        analyze_logs: List[str] = []
        analyze_logs.append("Analyzing product structure...")
        try:
            structure = get_product_structure(token, selected_product_ids, options, client)
            total_components = sum(len(p.components) for p in structure)
            total_features = sum(c.feature_count for p in structure for c in p.components)
            analyze_logs.append(
                f"Found {len(structure)} products, {total_components} components, {total_features} features"
            )

            # Warn if any component has 0 features
            for prod in structure:
                for comp in prod.components:
                    if comp.feature_count == 0:
                        warnings.append(
                            f"Component '{comp.name}' in '{prod.name}' has no features"
                        )

            steps.append(
                StepResult(
                    name="analyze_structure",
                    status=StepStatus.SUCCESS,
                    summary={
                        "products": len(structure),
                        "components": total_components,
                        "features": total_features,
                    },
                    logs=analyze_logs,
                )
            )

        except Exception as e:
            steps.append(
                StepResult(
                    name="analyze_structure",
                    status=StepStatus.ERROR,
                    summary={},
                    logs=analyze_logs,
                    error=str(e),
                )
            )
            errors.append(f"Structure analysis failed: {e}")

            return JobResult(
                job_id=job_id,
                mode=mode,
                company=company,
                website=website,
                selected_products=selected_products,
                steps=steps,
                warnings=warnings,
                errors=errors,
                completed_at=datetime.now(timezone.utc).isoformat(),
            )

    # Step 1: Generate mappings (flexible, based on actual structure)
    if mappings is None:
        step_logs: List[str] = []
        step_logs.append(f"Generating mappings for {company} ({website})...")

        try:
            mappings = generate_flexible_mappings(company, website, structure, anthropic_api_key)
            step_logs.append("AI-generated mappings created successfully")

            step = StepResult(
                name="generate_mappings",
                status=StepStatus.SUCCESS,
                summary={
                    "products": len(mappings.product_mapping.hierarchy),
                    "components": sum(
                        len(p.components) for p in mappings.product_mapping.hierarchy
                    ),
                    "features": sum(
                        len(c.features)
                        for p in mappings.product_mapping.hierarchy
                        for c in p.components
                    ),
                    "objectives": len(mappings.strategy_mapping.objectives),
                    "initiatives": len(mappings.strategy_mapping.initiatives),
                    "featuresList": len(mappings.features_list),
                },
                logs=step_logs,
            )

        except GenerationError as e:
            step_logs.append(f"AI generation failed: {e}")
            step_logs.append("Falling back to template-based generation...")

            try:
                mappings = generate_flexible_mappings_from_template(company, structure)
                step_logs.append("Template-based mappings created")
                warnings.append("Used template fallback instead of AI generation")

                step = StepResult(
                    name="generate_mappings",
                    status=StepStatus.SUCCESS,
                    summary={
                        "products": len(mappings.product_mapping.hierarchy),
                        "components": sum(
                            len(p.components) for p in mappings.product_mapping.hierarchy
                        ),
                        "features": sum(
                            len(c.features)
                            for p in mappings.product_mapping.hierarchy
                            for c in p.components
                        ),
                        "objectives": len(mappings.strategy_mapping.objectives),
                        "initiatives": len(mappings.strategy_mapping.initiatives),
                        "featuresList": len(mappings.features_list),
                        "fallback": True,
                    },
                    logs=step_logs,
                )

            except Exception as e2:
                step = StepResult(
                    name="generate_mappings",
                    status=StepStatus.ERROR,
                    summary={},
                    logs=step_logs,
                    error=str(e2),
                )
                steps.append(step)
                errors.append(f"Mapping generation failed: {e2}")

                return JobResult(
                    job_id=job_id,
                    mode=mode,
                    company=company,
                    website=website,
                    selected_products=selected_products,
                    steps=steps,
                    warnings=warnings,
                    errors=errors,
                    completed_at=datetime.now(timezone.utc).isoformat(),
                )

        steps.append(step)
    else:
        # Mappings provided - add a success step
        steps.append(
            StepResult(
                name="generate_mappings",
                status=StepStatus.SUCCESS,
                summary={"source": "provided"},
                logs=["Using provided mappings"],
            )
        )

    # Step 2: Validate preflight
    preflight_logs: List[str] = []
    preflight_logs.append("Running preflight validation...")

    preflight_result = preflight_check(
        token=token,
        selected_product_ids=selected_product_ids,
        product_mapping=mappings.product_mapping,
        strategy_mapping=mappings.strategy_mapping,
        features=mappings.features_list,
        client=client,
    )

    for error in preflight_result.errors:
        preflight_logs.append(f"Error: {error.field} - {error.message}")

    for warning in preflight_result.warnings:
        preflight_logs.append(f"Warning: {warning}")
        warnings.append(warning)

    if preflight_result.valid:
        preflight_logs.append("All preflight checks passed")
        steps.append(
            StepResult(
                name="validate_preflight",
                status=StepStatus.SUCCESS,
                summary={
                    "productsValid": True,
                    "mappingsValid": True,
                    "errorsCount": 0,
                    "warningsCount": len(preflight_result.warnings),
                },
                logs=preflight_logs,
            )
        )
    else:
        preflight_logs.append("Preflight validation failed")
        steps.append(
            StepResult(
                name="validate_preflight",
                status=StepStatus.ERROR,
                summary={
                    "productsValid": False,
                    "errorsCount": len(preflight_result.errors),
                    "warningsCount": len(preflight_result.warnings),
                },
                logs=preflight_logs,
                error="Preflight validation failed",
            )
        )

        # Add errors to job result
        for error in preflight_result.errors:
            errors.append(f"{error.field}: {error.message}")

        return JobResult(
            job_id=job_id,
            mode=mode,
            company=company,
            website=website,
            selected_products=selected_products,
            steps=steps,
            warnings=warnings,
            errors=errors,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

    # Step 3: Rename product hierarchy
    hierarchy_result = rename_hierarchy(
        token=token,
        mapping=mappings.product_mapping,
        selected_product_ids=selected_product_ids,
        apply=apply,
        client=client,
    )
    steps.append(hierarchy_result)

    if hierarchy_result.status == StepStatus.ERROR:
        errors.append(f"Hierarchy rename failed: {hierarchy_result.error}")
        # Continue with other steps even if this fails

    # Step 4: Rename strategy hierarchy
    strategy_result = rename_strategy(
        token=token,
        mapping=mappings.strategy_mapping,
        apply=apply,
        client=client,
    )
    steps.append(strategy_result)

    if strategy_result.status == StepStatus.ERROR:
        errors.append(f"Strategy rename failed: {strategy_result.error}")
        # Continue with other steps even if this fails

    # Step 5: Generate user insights
    insights_result = generate_insights(
        token=token,
        company=company,
        features=mappings.features_list,
        apply=apply,
        client=client,
    )
    steps.append(insights_result)

    if insights_result.status == StepStatus.ERROR:
        errors.append(f"Insights generation failed: {insights_result.error}")

    return JobResult(
        job_id=job_id,
        mode=mode,
        company=company,
        website=website,
        selected_products=selected_products,
        steps=steps,
        warnings=warnings,
        errors=errors,
        completed_at=datetime.now(timezone.utc).isoformat(),
    )


def run_poc_streaming(
    company: str,
    website: str,
    token: str,
    selected_product_ids: List[str],
    mode: str = "apply",  # Default to apply now (no more dry-run as default)
    mappings: Optional[GeneratedMappings] = None,
    anthropic_api_key: Optional[str] = None,
    client: Optional[ProductboardClient] = None,
    options: Optional[FlexibleOptions] = None,
):
    """
    Run the POC setup with streaming progress updates.

    Uses flexible generation that adapts to the actual structure of selected products.

    Yields events as each step completes:
    - {"type": "step", "step": StepResult}
    - {"type": "complete", "result": JobResult}
    """
    client = client or default_client
    options = options or FlexibleOptions()
    apply = mode == "apply"
    job_id = str(uuid.uuid4())

    steps: List[StepResult] = []
    warnings: List[str] = []
    errors: List[str] = []

    # Get product info for selected products
    selected_products: List[SelectedProduct] = []
    try:
        products = list_products(token, client)
        products_by_id = {p.id: p for p in products}
        for pid in selected_product_ids:
            if pid in products_by_id:
                p = products_by_id[pid]
                selected_products.append(SelectedProduct(id=p.id, name=p.name))
    except Exception:
        pass

    # Step 0: Analyze structure (needed for flexible generation)
    structure = []
    if mappings is None:
        analyze_logs: List[str] = []
        analyze_logs.append("Analyzing product structure...")
        try:
            structure = get_product_structure(token, selected_product_ids, options, client)
            total_components = sum(len(p.components) for p in structure)
            total_features = sum(c.feature_count for p in structure for c in p.components)
            analyze_logs.append(
                f"Found {len(structure)} products, {total_components} components, {total_features} features"
            )

            # Warn if any component has 0 features
            for prod in structure:
                for comp in prod.components:
                    if comp.feature_count == 0:
                        warnings.append(
                            f"Component '{comp.name}' in '{prod.name}' has no features"
                        )
                        analyze_logs.append(
                            f"Warning: Component '{comp.name}' has no features"
                        )

            analyze_step = StepResult(
                name="analyze_structure",
                status=StepStatus.SUCCESS,
                summary={
                    "products": len(structure),
                    "components": total_components,
                    "features": total_features,
                },
                logs=analyze_logs,
            )
            steps.append(analyze_step)
            yield {"type": "step", "step": analyze_step}

        except Exception as e:
            analyze_step = StepResult(
                name="analyze_structure",
                status=StepStatus.ERROR,
                summary={},
                logs=analyze_logs,
                error=str(e),
            )
            steps.append(analyze_step)
            yield {"type": "step", "step": analyze_step}
            errors.append(f"Structure analysis failed: {e}")

            yield {
                "type": "complete",
                "result": JobResult(
                    job_id=job_id,
                    mode=mode,
                    company=company,
                    website=website,
                    selected_products=selected_products,
                    steps=steps,
                    warnings=warnings,
                    errors=errors,
                    completed_at=datetime.now(timezone.utc).isoformat(),
                ),
            }
            return

    # Step 1: Generate mappings (flexible, based on actual structure)
    if mappings is None:
        step_logs: List[str] = []
        step_logs.append(f"Generating mappings for {company} ({website})...")

        try:
            mappings = generate_flexible_mappings(company, website, structure, anthropic_api_key)
            step_logs.append("AI-generated mappings created successfully")

            step = StepResult(
                name="generate_mappings",
                status=StepStatus.SUCCESS,
                summary={
                    "products": len(mappings.product_mapping.hierarchy),
                    "components": sum(len(p.components) for p in mappings.product_mapping.hierarchy),
                    "features": sum(len(c.features) for p in mappings.product_mapping.hierarchy for c in p.components),
                    "objectives": len(mappings.strategy_mapping.objectives),
                    "initiatives": len(mappings.strategy_mapping.initiatives),
                    "featuresList": len(mappings.features_list),
                },
                logs=step_logs,
            )

        except GenerationError as e:
            step_logs.append(f"AI generation failed: {e}")
            step_logs.append("Falling back to template-based generation...")

            try:
                mappings = generate_flexible_mappings_from_template(company, structure)
                step_logs.append("Template-based mappings created")
                warnings.append("Used template fallback instead of AI generation")

                step = StepResult(
                    name="generate_mappings",
                    status=StepStatus.SUCCESS,
                    summary={
                        "products": len(mappings.product_mapping.hierarchy),
                        "components": sum(len(p.components) for p in mappings.product_mapping.hierarchy),
                        "features": sum(len(c.features) for p in mappings.product_mapping.hierarchy for c in p.components),
                        "objectives": len(mappings.strategy_mapping.objectives),
                        "initiatives": len(mappings.strategy_mapping.initiatives),
                        "featuresList": len(mappings.features_list),
                        "fallback": True,
                    },
                    logs=step_logs,
                )

            except Exception as e2:
                step = StepResult(
                    name="generate_mappings",
                    status=StepStatus.ERROR,
                    summary={},
                    logs=step_logs,
                    error=str(e2),
                )
                steps.append(step)
                errors.append(f"Mapping generation failed: {e2}")
                yield {"type": "step", "step": step}

                yield {
                    "type": "complete",
                    "result": JobResult(
                        job_id=job_id,
                        mode=mode,
                        company=company,
                        website=website,
                        selected_products=selected_products,
                        steps=steps,
                        warnings=warnings,
                        errors=errors,
                        completed_at=datetime.now(timezone.utc).isoformat(),
                    ),
                }
                return

        steps.append(step)
        yield {"type": "step", "step": step}
    else:
        step = StepResult(
            name="generate_mappings",
            status=StepStatus.SUCCESS,
            summary={"source": "provided"},
            logs=["Using provided mappings"],
        )
        steps.append(step)
        yield {"type": "step", "step": step}

    # Step 2: Validate preflight
    preflight_logs: List[str] = []
    preflight_logs.append("Running preflight validation...")

    preflight_result = preflight_check(
        token=token,
        selected_product_ids=selected_product_ids,
        product_mapping=mappings.product_mapping,
        strategy_mapping=mappings.strategy_mapping,
        features=mappings.features_list,
        client=client,
    )

    for error in preflight_result.errors:
        preflight_logs.append(f"Error: {error.field} - {error.message}")

    for warning in preflight_result.warnings:
        preflight_logs.append(f"Warning: {warning}")
        warnings.append(warning)

    if preflight_result.valid:
        preflight_logs.append("All preflight checks passed")
        preflight_step = StepResult(
            name="validate_preflight",
            status=StepStatus.SUCCESS,
            summary={
                "productsValid": True,
                "mappingsValid": True,
                "errorsCount": 0,
                "warningsCount": len(preflight_result.warnings),
            },
            logs=preflight_logs,
        )
        steps.append(preflight_step)
        yield {"type": "step", "step": preflight_step}
    else:
        preflight_logs.append("Preflight validation failed")
        preflight_step = StepResult(
            name="validate_preflight",
            status=StepStatus.ERROR,
            summary={
                "productsValid": False,
                "errorsCount": len(preflight_result.errors),
                "warningsCount": len(preflight_result.warnings),
            },
            logs=preflight_logs,
            error="Preflight validation failed",
        )
        steps.append(preflight_step)
        yield {"type": "step", "step": preflight_step}

        for error in preflight_result.errors:
            errors.append(f"{error.field}: {error.message}")

        yield {
            "type": "complete",
            "result": JobResult(
                job_id=job_id,
                mode=mode,
                company=company,
                website=website,
                selected_products=selected_products,
                steps=steps,
                warnings=warnings,
                errors=errors,
                completed_at=datetime.now(timezone.utc).isoformat(),
            ),
        }
        return

    # Step 3: Rename product hierarchy
    hierarchy_result = rename_hierarchy(
        token=token,
        mapping=mappings.product_mapping,
        selected_product_ids=selected_product_ids,
        apply=apply,
        client=client,
    )
    steps.append(hierarchy_result)
    yield {"type": "step", "step": hierarchy_result}

    if hierarchy_result.status == StepStatus.ERROR:
        errors.append(f"Hierarchy rename failed: {hierarchy_result.error}")

    # Step 4: Rename strategy hierarchy
    strategy_result = rename_strategy(
        token=token,
        mapping=mappings.strategy_mapping,
        apply=apply,
        client=client,
    )
    steps.append(strategy_result)
    yield {"type": "step", "step": strategy_result}

    if strategy_result.status == StepStatus.ERROR:
        errors.append(f"Strategy rename failed: {strategy_result.error}")

    # Step 5: Generate user insights
    insights_result = generate_insights(
        token=token,
        company=company,
        features=mappings.features_list,
        apply=apply,
        client=client,
    )
    steps.append(insights_result)
    yield {"type": "step", "step": insights_result}

    if insights_result.status == StepStatus.ERROR:
        errors.append(f"Insights generation failed: {insights_result.error}")

    yield {
        "type": "complete",
        "result": JobResult(
            job_id=job_id,
            mode=mode,
            company=company,
            website=website,
            selected_products=selected_products,
            steps=steps,
            warnings=warnings,
            errors=errors,
            completed_at=datetime.now(timezone.utc).isoformat(),
        ),
    }

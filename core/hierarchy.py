"""
Product hierarchy operations.

Handles listing products and renaming the product/component/feature hierarchy.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .models import (
    AnalyzeResult,
    ComponentStructure,
    FlexibleOptions,
    ProductInfo,
    ProductMapping,
    ProductStructure,
    RenamePlan,
    StepResult,
    StepStatus,
    DEFAULT_MAX_COMPONENTS_PER_PRODUCT,
    DEFAULT_MAX_FEATURES_PER_COMPONENT,
)
from .pb_client import ProductboardClient, ProductboardError, default_client

# Minimum components for a product to be "eligible" for demo
MIN_COMPONENTS_FOR_ELIGIBILITY = 1


@dataclass
class HierarchyEntity:
    """An entity in the hierarchy (product, component, or feature)."""

    id: str
    name: str
    entity_type: str
    children: List["HierarchyEntity"] = field(default_factory=list)


@dataclass
class ProductHierarchy:
    """Complete product hierarchy tree."""

    products: List[HierarchyEntity]
    components_by_parent: Dict[str, List[HierarchyEntity]]
    features_by_parent: Dict[str, List[HierarchyEntity]]


def _get_entity_name(entity: Dict[str, Any]) -> str:
    """Extract name from entity."""
    return entity.get("name", "") or entity.get("fields", {}).get("name", "")


def _get_child_ids(entity: Dict[str, Any], child_type: str) -> List[str]:
    """Extract child IDs from entity relationships."""
    child_ids = []
    relationships = entity.get("relationships", {})
    rel_data = relationships.get("data", [])

    for rel in rel_data:
        if rel.get("type") == "child":
            target = rel.get("target", {})
            if target.get("type") == child_type:
                child_id = target.get("id")
                if child_id:
                    child_ids.append(child_id)

    return child_ids


def build_hierarchy(
    token: str,
    client: Optional[ProductboardClient] = None,
    logs: Optional[List[str]] = None,
) -> ProductHierarchy:
    """
    Build the complete product hierarchy tree.

    Fetches all products, components, and features, then organizes them
    into a tree structure sorted by name.
    """
    client = client or default_client
    logs = logs if logs is not None else []

    logs.append("Fetching hierarchy from Productboard...")

    # Fetch all entities
    products_raw = client.fetch_products(token)
    components_raw = client.fetch_components(token)
    features_raw = client.fetch_features(token)

    logs.append(
        f"Found {len(products_raw)} products, {len(components_raw)} components, {len(features_raw)} features"
    )

    # Create lookup dictionaries
    components_by_id = {c.get("id"): c for c in components_raw}
    features_by_id = {f.get("id"): f for f in features_raw}

    # Sort products by name
    products_raw.sort(key=lambda p: _get_entity_name(p).lower())

    # Build products list
    products = []
    components_by_parent: Dict[str, List[HierarchyEntity]] = {}
    features_by_parent: Dict[str, List[HierarchyEntity]] = {}

    for product in products_raw:
        product_id = product.get("id")
        product_name = _get_entity_name(product)

        # Get components for this product
        child_component_ids = _get_child_ids(product, "component")
        product_components = []

        for cid in child_component_ids:
            if cid in components_by_id:
                comp = components_by_id[cid]
                comp_name = _get_entity_name(comp)
                product_components.append(
                    HierarchyEntity(id=cid, name=comp_name, entity_type="component")
                )

        # Sort components by name
        product_components.sort(key=lambda c: c.name.lower())
        components_by_parent[product_id] = product_components

        # Get features for each component
        for comp_raw in [components_by_id.get(cid) for cid in child_component_ids if cid in components_by_id]:
            if not comp_raw:
                continue
            comp_id = comp_raw.get("id")
            child_feature_ids = _get_child_ids(comp_raw, "feature")
            comp_features = []

            for fid in child_feature_ids:
                if fid in features_by_id:
                    feat = features_by_id[fid]
                    feat_name = _get_entity_name(feat)
                    comp_features.append(
                        HierarchyEntity(id=fid, name=feat_name, entity_type="feature")
                    )

            # Sort features by name
            comp_features.sort(key=lambda f: f.name.lower())
            features_by_parent[comp_id] = comp_features

        products.append(
            HierarchyEntity(id=product_id, name=product_name, entity_type="product")
        )

    return ProductHierarchy(
        products=products,
        components_by_parent=components_by_parent,
        features_by_parent=features_by_parent,
    )


def list_products(
    token: str,
    client: Optional[ProductboardClient] = None,
) -> List[ProductInfo]:
    """
    List all products with their component and feature counts.

    Returns a list of ProductInfo sorted by name, with eligibility info.
    """
    client = client or default_client

    hierarchy = build_hierarchy(token, client)

    products_info = []
    for product in hierarchy.products:
        components = hierarchy.components_by_parent.get(product.id, [])
        component_count = len(components)

        # Count features across all components
        feature_count = sum(
            len(hierarchy.features_by_parent.get(comp.id, []))
            for comp in components
        )

        # Determine eligibility
        eligible = component_count >= MIN_COMPONENTS_FOR_ELIGIBILITY
        ineligible_reason = None
        if not eligible:
            ineligible_reason = "No components"

        products_info.append(
            ProductInfo(
                id=product.id,
                name=product.name,
                component_count=component_count,
                feature_count=feature_count,
                eligible=eligible,
                ineligible_reason=ineligible_reason,
            )
        )

    return products_info


def analyze_space(
    token: str,
    client: Optional[ProductboardClient] = None,
) -> AnalyzeResult:
    """
    Analyze a Productboard space and return product info with eligibility.

    Returns AnalyzeResult with products and recommendations.
    """
    client = client or default_client
    warnings: List[str] = []

    products = list_products(token, client)

    # Determine auto-select recommendations
    eligible_products = [p for p in products if p.eligible]
    auto_select_ids: List[str] = []

    if len(eligible_products) == 0:
        warnings.append("No eligible products found. All products need at least 1 component.")
    elif len(eligible_products) == 1:
        auto_select_ids = [eligible_products[0].id]
        warnings.append("Only 1 eligible product found. You can proceed with 1 product.")
    elif len(eligible_products) == 2:
        auto_select_ids = [p.id for p in eligible_products[:2]]
    else:
        # More than 2 eligible - let user choose, but suggest first 2 by name
        auto_select_ids = [p.id for p in eligible_products[:2]]

    return AnalyzeResult(
        products=products,
        warnings=warnings,
        auto_select_product_ids=auto_select_ids,
    )


def get_product_structure(
    token: str,
    product_ids: List[str],
    options: Optional[FlexibleOptions] = None,
    client: Optional[ProductboardClient] = None,
) -> List[ProductStructure]:
    """
    Get detailed structure for selected products (components and features).

    Respects the caps in options for max components/features.
    """
    client = client or default_client
    options = options or FlexibleOptions()

    hierarchy = build_hierarchy(token, client)

    # Create lookup
    products_by_id = {p.id: p for p in hierarchy.products}

    structures = []
    for product_id in product_ids:
        if product_id not in products_by_id:
            continue

        product = products_by_id[product_id]
        components = hierarchy.components_by_parent.get(product_id, [])

        # Cap components
        capped_components = components[:options.max_components_per_product]

        component_structures = []
        for comp in capped_components:
            features = hierarchy.features_by_parent.get(comp.id, [])
            # Cap features
            capped_features = features[:options.max_features_per_component]

            component_structures.append(
                ComponentStructure(
                    id=comp.id,
                    name=comp.name,
                    feature_count=len(capped_features),
                    features=[{"id": f.id, "name": f.name} for f in capped_features],
                )
            )

        structures.append(
            ProductStructure(
                id=product_id,
                name=product.name,
                components=component_structures,
            )
        )

    return structures


def rename_hierarchy(
    token: str,
    mapping: ProductMapping,
    selected_product_ids: List[str],
    apply: bool = False,
    client: Optional[ProductboardClient] = None,
) -> StepResult:
    """
    Rename products, components, and features based on mapping.

    Args:
        token: Productboard API token
        mapping: ProductMapping with new names
        selected_product_ids: IDs of the 2 products to rename (in order)
        apply: If True, actually apply changes; if False, dry-run
        client: Optional ProductboardClient instance

    Returns:
        StepResult with summary and logs
    """
    client = client or default_client
    logs: List[str] = []
    stats = {"updated": 0, "skipped": 0, "errors": 0, "missing": 0}

    try:
        # Build hierarchy
        hierarchy = build_hierarchy(token, client, logs)

        # Create a map of selected product IDs to their positions in mapping
        # selected_product_ids[0] -> mapping.hierarchy[0]
        # selected_product_ids[1] -> mapping.hierarchy[1]
        product_id_to_position = {pid: idx for idx, pid in enumerate(selected_product_ids)}

        # Find the products by ID
        products_by_id = {p.id: p for p in hierarchy.products}

        mode_str = "APPLY" if apply else "DRY-RUN"
        logs.append(f"Processing hierarchy rename ({mode_str} mode)...")

        for selected_idx, product_id in enumerate(selected_product_ids):
            if product_id not in products_by_id:
                logs.append(f"Product ID {product_id} not found in space")
                stats["missing"] += 1
                continue

            product = products_by_id[product_id]

            # Get the corresponding mapping
            if selected_idx >= len(mapping.hierarchy):
                logs.append(f"No mapping for position {selected_idx + 1}")
                stats["missing"] += 1
                continue

            product_mapping = mapping.hierarchy[selected_idx]

            # Rename product
            if product_mapping.new_name:
                if product.name == product_mapping.new_name:
                    logs.append(f"[Product] '{product.name}' - Skipped (names identical)")
                    stats["skipped"] += 1
                elif apply:
                    try:
                        if client.update_entity(token, product.id, product_mapping.new_name):
                            logs.append(
                                f"[Product] '{product.name}' -> '{product_mapping.new_name}' - Updated"
                            )
                            stats["updated"] += 1
                        else:
                            logs.append(
                                f"[Product] '{product.name}' -> '{product_mapping.new_name}' - Failed"
                            )
                            stats["errors"] += 1
                    except ProductboardError as e:
                        logs.append(f"[Product] '{product.name}' - Error: {e}")
                        stats["errors"] += 1
                else:
                    logs.append(
                        f"[Product] '{product.name}' -> '{product_mapping.new_name}' - Would update"
                    )
                    stats["updated"] += 1

            # Get components for this product
            components = hierarchy.components_by_parent.get(product.id, [])

            for comp_mapping in product_mapping.components:
                comp_pos = comp_mapping.position - 1  # Convert to 0-indexed

                if comp_pos < 0 or comp_pos >= len(components):
                    logs.append(
                        f"  [Component {comp_pos + 1}] Position out of range (have {len(components)})"
                    )
                    stats["missing"] += 1
                    continue

                component = components[comp_pos]

                # Rename component
                if comp_mapping.new_name:
                    if component.name == comp_mapping.new_name:
                        logs.append(
                            f"  [Component] '{component.name}' - Skipped (names identical)"
                        )
                        stats["skipped"] += 1
                    elif apply:
                        try:
                            if client.update_entity(token, component.id, comp_mapping.new_name):
                                logs.append(
                                    f"  [Component] '{component.name}' -> '{comp_mapping.new_name}' - Updated"
                                )
                                stats["updated"] += 1
                            else:
                                logs.append(
                                    f"  [Component] '{component.name}' -> '{comp_mapping.new_name}' - Failed"
                                )
                                stats["errors"] += 1
                        except ProductboardError as e:
                            logs.append(f"  [Component] '{component.name}' - Error: {e}")
                            stats["errors"] += 1
                    else:
                        logs.append(
                            f"  [Component] '{component.name}' -> '{comp_mapping.new_name}' - Would update"
                        )
                        stats["updated"] += 1

                # Get features for this component
                features = hierarchy.features_by_parent.get(component.id, [])

                for feat_mapping in comp_mapping.features:
                    feat_pos = feat_mapping.position - 1  # Convert to 0-indexed

                    if feat_pos < 0 or feat_pos >= len(features):
                        logs.append(
                            f"    [Feature {feat_pos + 1}] Position out of range (have {len(features)})"
                        )
                        stats["missing"] += 1
                        continue

                    feature = features[feat_pos]

                    # Rename feature
                    if feat_mapping.new_name:
                        if feature.name == feat_mapping.new_name:
                            logs.append(
                                f"    [Feature] '{feature.name}' - Skipped (names identical)"
                            )
                            stats["skipped"] += 1
                        elif apply:
                            try:
                                if client.update_entity(
                                    token, feature.id, feat_mapping.new_name
                                ):
                                    logs.append(
                                        f"    [Feature] '{feature.name}' -> '{feat_mapping.new_name}' - Updated"
                                    )
                                    stats["updated"] += 1
                                else:
                                    logs.append(
                                        f"    [Feature] '{feature.name}' -> '{feat_mapping.new_name}' - Failed"
                                    )
                                    stats["errors"] += 1
                            except ProductboardError as e:
                                logs.append(f"    [Feature] '{feature.name}' - Error: {e}")
                                stats["errors"] += 1
                        else:
                            logs.append(
                                f"    [Feature] '{feature.name}' -> '{feat_mapping.new_name}' - Would update"
                            )
                            stats["updated"] += 1

        # Determine status
        status = StepStatus.SUCCESS if stats["errors"] == 0 else StepStatus.ERROR

        return StepResult(
            name="rename_hierarchy",
            status=status,
            summary=stats,
            logs=logs,
            error=f"{stats['errors']} errors occurred" if stats["errors"] > 0 else None,
        )

    except ProductboardError as e:
        return StepResult(
            name="rename_hierarchy",
            status=StepStatus.ERROR,
            summary=stats,
            logs=logs,
            error=str(e),
        )

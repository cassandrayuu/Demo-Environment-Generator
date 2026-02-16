#!/usr/bin/env python3
"""
Productboard Entity Rename Script (Position-Based)

Renames existing Productboard entities (products, components, features)
based on hierarchical position, not current names.
Does NOT create, delete, or modify relationships.
"""

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import requests

API_BASE = "https://api.productboard.com/v2"
MAX_RETRIES = 5
INITIAL_BACKOFF = 1.0


def get_token() -> str:
    token = os.environ.get("PB_TOKEN")
    if not token:
        print("Error: PB_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    return token


def make_request(
    method: str,
    url: str,
    token: str,
    json_data: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> requests.Response:
    """Make HTTP request with retry logic for 429 and 5xx errors."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Version": "1",
    }

    backoff = INITIAL_BACKOFF
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=json_data,
                params=params,
                timeout=30,
            )

            if response.status_code == 429 or (500 <= response.status_code < 600):
                if attempt < MAX_RETRIES - 1:
                    retry_after = response.headers.get("Retry-After")
                    wait_time = float(retry_after) if retry_after else backoff
                    print(f"  Retrying in {wait_time:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})...")
                    time.sleep(wait_time)
                    backoff *= 2
                    continue

            return response

        except requests.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                print(f"  Request error: {e}. Retrying in {backoff:.1f}s...")
                time.sleep(backoff)
                backoff *= 2
                continue
            raise

    return response


def fetch_all_entities(token: str, entity_type: str) -> list[dict[str, Any]]:
    """Fetch all entities of a given type with pagination."""
    entities = []
    url = f"{API_BASE}/entities"
    params = {"type": entity_type}

    while url:
        response = make_request("GET", url, token, params=params)

        if response.status_code != 200:
            snippet = response.text[:200] if response.text else "(empty)"
            print(f"  Fetch failed: HTTP {response.status_code} - {snippet}", file=sys.stderr)
            return entities

        data = response.json()
        entities.extend(data.get("data", []))

        # Handle pagination
        links = data.get("links", {})
        url = links.get("next")
        params = None  # Next URL includes params

    return entities


def get_entity_name(entity: dict[str, Any]) -> str:
    """Extract name from entity."""
    return entity.get("name", "") or entity.get("fields", {}).get("name", "")


def get_child_ids(entity: dict[str, Any], child_type: str) -> list[str]:
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


def build_hierarchy(token: str, debug: bool = False) -> dict[str, Any]:
    """
    Fetch all products, components, and features, then build a hierarchy tree.
    Returns a dict with products sorted by name, each containing sorted components,
    each containing sorted features.
    """
    print("Fetching hierarchy from Productboard...")

    products = fetch_all_entities(token, "product")
    components = fetch_all_entities(token, "component")
    features = fetch_all_entities(token, "feature")

    print(f"  Found {len(products)} products, {len(components)} components, {len(features)} features")

    if debug:
        print("\n[DEBUG] Sample product structure:")
        if products:
            print(json.dumps(products[0], indent=2, default=str)[:1000])
        print("\n[DEBUG] Sample component structure:")
        if components:
            print(json.dumps(components[0], indent=2, default=str)[:1000])
        print("\n[DEBUG] Sample feature structure:")
        if features:
            print(json.dumps(features[0], indent=2, default=str)[:1000])

    # Create lookup dictionaries by ID
    components_by_id = {c.get("id"): c for c in components}
    features_by_id = {f.get("id"): f for f in features}

    # Sort products by name for consistent ordering
    products.sort(key=lambda p: get_entity_name(p).lower())

    # Build component lookup by parent product ID (using parent's child references)
    components_by_parent: dict[str, list[dict]] = {}
    for product in products:
        product_id = product.get("id")
        child_component_ids = get_child_ids(product, "component")
        product_components = []
        for cid in child_component_ids:
            if cid in components_by_id:
                product_components.append(components_by_id[cid])
        # Sort by name
        product_components.sort(key=lambda c: get_entity_name(c).lower())
        components_by_parent[product_id] = product_components

    # Build feature lookup by parent component ID (using parent's child references)
    features_by_parent: dict[str, list[dict]] = {}
    for comp in components:
        comp_id = comp.get("id")
        child_feature_ids = get_child_ids(comp, "feature")
        comp_features = []
        for fid in child_feature_ids:
            if fid in features_by_id:
                comp_features.append(features_by_id[fid])
        # Sort by name
        comp_features.sort(key=lambda f: get_entity_name(f).lower())
        features_by_parent[comp_id] = comp_features

    return {
        "products": products,
        "components_by_parent": components_by_parent,
        "features_by_parent": features_by_parent,
    }


def update_entity(token: str, entity_id: str, new_name: str) -> bool:
    """Update an entity's name via PATCH."""
    url = f"{API_BASE}/entities/{entity_id}"
    payload = {
        "data": {
            "fields": {
                "name": new_name
            }
        }
    }

    response = make_request("PATCH", url, token, payload)

    if response.status_code in (200, 204):
        return True

    snippet = response.text[:200] if response.text else "(empty)"
    print(f"  Update failed: HTTP {response.status_code} - {snippet}", file=sys.stderr)
    return False


def load_mapping(filepath: str) -> dict[str, Any]:
    """Load and validate the JSON mapping file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Mapping file not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in mapping file: {e}", file=sys.stderr)
        sys.exit(1)

    if "hierarchy" not in data or not isinstance(data["hierarchy"], list):
        print("Error: Mapping file must contain a 'hierarchy' array.", file=sys.stderr)
        sys.exit(1)

    return data


def compute_mapping_expectations(mapping: dict[str, Any]) -> dict[str, int]:
    """Count how many entities the mapping expects to rename."""
    expected_products = 0
    expected_components = 0
    expected_features = 0

    for product_mapping in mapping.get("hierarchy", []):
        if product_mapping.get("newName"):
            expected_products += 1
        for comp_mapping in product_mapping.get("components", []):
            if comp_mapping.get("newName"):
                expected_components += 1
            for feat_mapping in comp_mapping.get("features", []):
                if feat_mapping.get("newName"):
                    expected_features += 1

    return {
        "products": expected_products,
        "components": expected_components,
        "features": expected_features,
    }


def compute_renameable_counts(
    mapping: dict[str, Any],
    hierarchy: dict[str, Any],
) -> dict[str, int]:
    """Count how many entities can actually be renamed based on what exists."""
    products = hierarchy["products"]
    components_by_parent = hierarchy["components_by_parent"]
    features_by_parent = hierarchy["features_by_parent"]

    renameable_products = 0
    renameable_components = 0
    renameable_features = 0

    for product_mapping in mapping.get("hierarchy", []):
        product_pos = product_mapping.get("position", 0) - 1
        if product_mapping.get("newName") and 0 <= product_pos < len(products):
            renameable_products += 1
            product = products[product_pos]
            product_id = product.get("id")
            product_components = components_by_parent.get(product_id, [])

            for comp_mapping in product_mapping.get("components", []):
                comp_pos = comp_mapping.get("position", 0) - 1
                if comp_mapping.get("newName") and 0 <= comp_pos < len(product_components):
                    renameable_components += 1
                    component = product_components[comp_pos]
                    component_id = component.get("id")
                    component_features = features_by_parent.get(component_id, [])

                    for feat_mapping in comp_mapping.get("features", []):
                        feat_pos = feat_mapping.get("position", 0) - 1
                        if feat_mapping.get("newName") and 0 <= feat_pos < len(component_features):
                            renameable_features += 1

    return {
        "products": renameable_products,
        "components": renameable_components,
        "features": renameable_features,
    }


def print_preflight_summary(
    hierarchy: dict[str, Any],
    expected: dict[str, int],
    renameable: dict[str, int],
) -> None:
    """Print a summary comparing the space hierarchy to mapping expectations."""
    products = hierarchy["products"]
    total_components = sum(len(c) for c in hierarchy["components_by_parent"].values())
    total_features = sum(len(f) for f in hierarchy["features_by_parent"].values())

    print("\nPre-flight check:")
    print(f"  Your space:      {len(products)} products, {total_components} components, {total_features} features")
    print(f"  Mapping expects: {expected['products']} products, {expected['components']} components, {expected['features']} features")
    print(f"  Will rename:     {renameable['products']} products, {renameable['components']} components, {renameable['features']} features")

    total_expected = expected["products"] + expected["components"] + expected["features"]
    total_renameable = renameable["products"] + renameable["components"] + renameable["features"]

    if total_renameable < total_expected:
        print(f"\n  ⚠ Note: {total_expected - total_renameable} entities in mapping exceed your hierarchy positions")


def get_selection_file_path(mapping_file: str) -> Path:
    """Get path to the selection file for a given mapping file."""
    mapping_path = Path(mapping_file).resolve()
    return mapping_path.parent / f".{mapping_path.stem}_selection.json"


def save_selection(mapping_file: str, product_positions: list[int]) -> None:
    """Save product position selection to a file."""
    selection_path = get_selection_file_path(mapping_file)
    with open(selection_path, "w", encoding="utf-8") as f:
        json.dump({"product_positions": product_positions}, f)
    print(f"\n✓ Selection saved to {selection_path}")


def load_selection(mapping_file: str) -> list[int] | None:
    """Load product position selection from file if it exists."""
    selection_path = get_selection_file_path(mapping_file)
    if not selection_path.exists():
        return None
    try:
        with open(selection_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("product_positions")
    except (json.JSONDecodeError, KeyError):
        return None


def display_products_for_selection(
    hierarchy: dict[str, Any],
    mapping: dict[str, Any],
) -> None:
    """Display products in the space for user selection."""
    products = hierarchy["products"]
    components_by_parent = hierarchy["components_by_parent"]

    num_mapping_products = len(mapping.get("hierarchy", []))

    print(f"\nYour space has {len(products)} products:")
    print("-" * 50)

    for i, product in enumerate(products):
        product_id = product.get("id")
        product_name = get_entity_name(product)
        num_components = len(components_by_parent.get(product_id, []))
        print(f"  {i + 1}. {product_name} ({num_components} components)")

    print("-" * 50)
    print(f"\nMapping needs {num_mapping_products} products.")

    # Show what each mapping slot expects
    print("\nMapping structure:")
    for idx, prod_map in enumerate(mapping.get("hierarchy", []), 1):
        new_name = prod_map.get("newName", "(unnamed)")
        num_comps = len(prod_map.get("components", []))
        print(f"  Slot {idx}: \"{new_name}\" ({num_comps} components)")


def interactive_select(
    hierarchy: dict[str, Any],
    mapping: dict[str, Any],
    mapping_file: str,
) -> None:
    """Run interactive product selection mode."""
    display_products_for_selection(hierarchy, mapping)

    num_mapping_products = len(mapping.get("hierarchy", []))

    print(f"\nSelect {num_mapping_products} products to rename (e.g., \"1,3\" or \"1 3\"):")
    try:
        user_input = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nSelection cancelled.")
        sys.exit(0)

    # Parse input - support comma or space separated
    parts = user_input.replace(",", " ").split()
    try:
        positions = [int(p) for p in parts]
    except ValueError:
        print("Error: Please enter numbers only (e.g., \"1,3\" or \"1 3\")", file=sys.stderr)
        sys.exit(1)

    # Validate positions
    num_products = len(hierarchy["products"])
    for pos in positions:
        if pos < 1 or pos > num_products:
            print(f"Error: Position {pos} is out of range (1-{num_products})", file=sys.stderr)
            sys.exit(1)

    if len(positions) != num_mapping_products:
        print(f"Warning: You selected {len(positions)} products but mapping expects {num_mapping_products}.")
        print("Proceeding with your selection...")

    save_selection(mapping_file, positions)
    print(f"\nNow run with --dry-run or --apply to execute.")


def remap_positions(mapping: dict[str, Any], selected_positions: list[int]) -> dict[str, Any]:
    """Update mapping to use selected product positions."""
    new_mapping = mapping.copy()
    new_hierarchy = []

    for idx, prod_map in enumerate(mapping.get("hierarchy", [])):
        if idx < len(selected_positions):
            new_prod = prod_map.copy()
            new_prod["position"] = selected_positions[idx]
            new_hierarchy.append(new_prod)
        else:
            new_hierarchy.append(prod_map)

    new_mapping["hierarchy"] = new_hierarchy
    return new_mapping


def process_hierarchy(
    mapping: dict[str, Any],
    hierarchy: dict[str, Any],
    token: str,
    apply: bool,
) -> dict[str, int]:
    """Process the mapping and rename entities by position."""
    stats = {
        "updated": 0,
        "skipped": 0,
        "missing": 0,
        "errors": 0,
    }

    products = hierarchy["products"]
    components_by_parent = hierarchy["components_by_parent"]
    features_by_parent = hierarchy["features_by_parent"]

    for product_mapping in mapping.get("hierarchy", []):
        product_pos = product_mapping.get("position", 0) - 1  # Convert to 0-indexed
        product_new_name = product_mapping.get("newName", "")

        if product_pos < 0 or product_pos >= len(products):
            print(f"\n[Product {product_pos + 1}] Position out of range (have {len(products)} products)")
            stats["missing"] += 1
            continue

        product = products[product_pos]
        product_id = product.get("id")
        product_current_name = get_entity_name(product)

        # Rename product
        if product_new_name:
            print(f"\n[Product {product_pos + 1}] '{product_current_name}' -> '{product_new_name}'")
            if product_current_name == product_new_name:
                print("  Skipped: Names are identical")
                stats["skipped"] += 1
            elif apply:
                if update_entity(token, product_id, product_new_name):
                    print(f"  Updated: {product_id}")
                    stats["updated"] += 1
                else:
                    print(f"  Error: Failed to update {product_id}")
                    stats["errors"] += 1
            else:
                print(f"  Would update: {product_id}")
                stats["updated"] += 1

        # Process components under this product
        product_components = components_by_parent.get(product_id, [])

        for component_mapping in product_mapping.get("components", []):
            comp_pos = component_mapping.get("position", 0) - 1
            comp_new_name = component_mapping.get("newName", "")

            if comp_pos < 0 or comp_pos >= len(product_components):
                print(f"\n  [Component {comp_pos + 1}] Position out of range (have {len(product_components)} components under this product)")
                stats["missing"] += 1
                continue

            component = product_components[comp_pos]
            component_id = component.get("id")
            component_current_name = get_entity_name(component)

            # Rename component
            if comp_new_name:
                print(f"\n  [Component {comp_pos + 1}] '{component_current_name}' -> '{comp_new_name}'")
                if component_current_name == comp_new_name:
                    print("    Skipped: Names are identical")
                    stats["skipped"] += 1
                elif apply:
                    if update_entity(token, component_id, comp_new_name):
                        print(f"    Updated: {component_id}")
                        stats["updated"] += 1
                    else:
                        print(f"    Error: Failed to update {component_id}")
                        stats["errors"] += 1
                else:
                    print(f"    Would update: {component_id}")
                    stats["updated"] += 1

            # Process features under this component
            component_features = features_by_parent.get(component_id, [])

            for feature_mapping in component_mapping.get("features", []):
                feat_pos = feature_mapping.get("position", 0) - 1
                feat_new_name = feature_mapping.get("newName", "")

                if feat_pos < 0 or feat_pos >= len(component_features):
                    print(f"\n    [Feature {feat_pos + 1}] Position out of range (have {len(component_features)} features under this component)")
                    stats["missing"] += 1
                    continue

                feature = component_features[feat_pos]
                feature_id = feature.get("id")
                feature_current_name = get_entity_name(feature)

                # Rename feature
                if feat_new_name:
                    print(f"\n    [Feature {feat_pos + 1}] '{feature_current_name}' -> '{feat_new_name}'")
                    if feature_current_name == feat_new_name:
                        print("      Skipped: Names are identical")
                        stats["skipped"] += 1
                    elif apply:
                        if update_entity(token, feature_id, feat_new_name):
                            print(f"      Updated: {feature_id}")
                            stats["updated"] += 1
                        else:
                            print(f"      Error: Failed to update {feature_id}")
                            stats["errors"] += 1
                    else:
                        print(f"      Would update: {feature_id}")
                        stats["updated"] += 1

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rename Productboard entities based on hierarchical position."
    )
    parser.add_argument("mapping_file", help="Path to the JSON mapping file")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--select",
        action="store_true",
        help="Interactively select which products to rename",
    )
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them",
    )
    group.add_argument(
        "--apply",
        action="store_true",
        help="Actually apply the rename updates",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print debug info about entity structure",
    )

    args = parser.parse_args()

    token = get_token()
    mapping = load_mapping(args.mapping_file)

    customer = mapping.get("customer", "Unknown")

    print(f"Customer: {customer}")
    if args.select:
        print("Mode: SELECT")
    else:
        print(f"Mode: {'APPLY' if args.apply else 'DRY-RUN'}")
    print("-" * 60)

    # Fetch and build hierarchy
    hierarchy = build_hierarchy(token, debug=args.debug)

    # Handle --select mode
    if args.select:
        interactive_select(hierarchy, mapping, args.mapping_file)
        sys.exit(0)

    # Check for saved selection and remap if found
    saved_selection = load_selection(args.mapping_file)
    if saved_selection:
        print(f"\nUsing saved selection: products {saved_selection}")
        mapping = remap_positions(mapping, saved_selection)

    # Pre-flight summary
    expected = compute_mapping_expectations(mapping)
    renameable = compute_renameable_counts(mapping, hierarchy)
    print_preflight_summary(hierarchy, expected, renameable)

    print("\n" + "-" * 60)
    print("Processing updates by position...")

    stats = process_hierarchy(mapping, hierarchy, token, args.apply)

    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Updated:   {stats['updated']}")
    print(f"  Skipped:   {stats['skipped']}")
    print(f"  Missing:   {stats['missing']}")
    print(f"  Errors:    {stats['errors']}")

    if not args.apply and stats["updated"] > 0:
        print("\nThis was a dry-run. Use --apply to execute updates.")

    # Exit codes: 0=success, 1=errors occurred
    if stats["errors"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

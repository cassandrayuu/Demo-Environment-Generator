#!/usr/bin/env python3
"""
Productboard Strategy Rename Script (Position-Based)

Renames existing Productboard strategic entities (objectives, key results, initiatives)
based on hierarchical position, not current names.
Does NOT create, delete, or modify relationships.
"""

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

import requests

API_BASE = "https://api.productboard.com"
MAX_RETRIES = 5
INITIAL_BACKOFF = 1.0

# Minimum counts required
MIN_OBJECTIVES = 3
MIN_KEY_RESULTS_PER_OBJECTIVE = 2
MIN_INITIATIVES = 6  # Global initiatives list


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
    json_data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
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


def fetch_all_paginated(
    token: str,
    url: str,
    params: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Fetch all entities with pagination support."""
    entities = []
    current_params = params.copy() if params else {}

    while url:
        response = make_request("GET", url, token, params=current_params)

        if response.status_code != 200:
            snippet = response.text[:200] if response.text else "(empty)"
            print(f"  API Error: HTTP {response.status_code} - {snippet}", file=sys.stderr)
            return entities

        data = response.json()
        entities.extend(data.get("data", []))

        # Handle pagination
        links = data.get("links", {})
        url = links.get("next")
        current_params = {}  # Next URL includes params

    return entities


def fetch_objectives(token: str) -> List[Dict[str, Any]]:
    """Fetch all objectives."""
    url = f"{API_BASE}/objectives"
    return fetch_all_paginated(token, url)


def fetch_key_results(token: str, objective_id: str) -> List[Dict[str, Any]]:
    """Fetch key results for a specific objective."""
    url = f"{API_BASE}/key-results"
    params = {"objective.id": objective_id}
    return fetch_all_paginated(token, url, params)


def fetch_initiatives(token: str) -> List[Dict[str, Any]]:
    """Fetch all initiatives (global list, not per-objective)."""
    url = f"{API_BASE}/initiatives"
    return fetch_all_paginated(token, url)


def get_entity_name(entity: Dict[str, Any]) -> str:
    """Extract name from entity."""
    return entity.get("name", "") or ""


def update_objective(token: str, objective_id: str, new_name: str) -> bool:
    """Update an objective's name via PATCH."""
    url = f"{API_BASE}/objectives/{objective_id}"
    payload = {"data": {"name": new_name}}

    response = make_request("PATCH", url, token, payload)

    if response.status_code in (200, 204):
        return True

    snippet = response.text[:200] if response.text else "(empty)"
    print(f"  API Error: HTTP {response.status_code} - {snippet}", file=sys.stderr)
    return False


def update_key_result(token: str, kr_id: str, new_name: str) -> bool:
    """Update a key result's name via PATCH."""
    url = f"{API_BASE}/key-results/{kr_id}"
    payload = {"data": {"name": new_name}}

    response = make_request("PATCH", url, token, payload)

    if response.status_code in (200, 204):
        return True

    snippet = response.text[:200] if response.text else "(empty)"
    print(f"  API Error: HTTP {response.status_code} - {snippet}", file=sys.stderr)
    return False


def update_initiative(token: str, initiative_id: str, new_name: str) -> bool:
    """Update an initiative's name via PATCH."""
    url = f"{API_BASE}/initiatives/{initiative_id}"
    payload = {"data": {"name": new_name}}

    response = make_request("PATCH", url, token, payload)

    if response.status_code in (200, 204):
        return True

    snippet = response.text[:200] if response.text else "(empty)"
    print(f"  API Error: HTTP {response.status_code} - {snippet}", file=sys.stderr)
    return False


def load_mapping(filepath: str) -> Dict[str, Any]:
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

    # Validate required arrays
    if "objectives" not in data or not isinstance(data["objectives"], list):
        print("Error: Mapping file must contain an 'objectives' array.", file=sys.stderr)
        sys.exit(1)

    if "initiatives" not in data or not isinstance(data["initiatives"], list):
        print("Error: Mapping file must contain an 'initiatives' array.", file=sys.stderr)
        sys.exit(1)

    return data


def process_objectives_and_key_results(
    mapping: Dict[str, Any],
    objectives: List[Dict[str, Any]],
    token: str,
    apply: bool,
) -> Dict[str, int]:
    """Process objectives and their key results by position."""
    stats = {
        "updated": 0,
        "skipped": 0,
        "missing": 0,
        "out_of_range": 0,
        "errors": 0,
    }

    for obj_mapping in mapping.get("objectives", []):
        obj_pos = obj_mapping.get("position", 0) - 1  # Convert to 0-indexed
        obj_new_name = obj_mapping.get("newName", "")

        if obj_pos < 0 or obj_pos >= len(objectives):
            print(f"\n[Objective position {obj_pos + 1}] Position out of range (have {len(objectives)} objectives)")
            stats["out_of_range"] += 1
            continue

        objective = objectives[obj_pos]
        objective_id = objective.get("id")
        objective_current_name = get_entity_name(objective)

        # Rename objective
        if obj_new_name:
            print(f"\n[Objective {obj_pos + 1}] '{objective_current_name}' -> '{obj_new_name}'")
            if objective_current_name == obj_new_name:
                print("  Skipped: Names are identical")
                stats["skipped"] += 1
            elif apply:
                if update_objective(token, objective_id, obj_new_name):
                    print(f"  Updated: {objective_id}")
                    stats["updated"] += 1
                else:
                    print(f"  Error: Failed to update {objective_id}")
                    stats["errors"] += 1
            else:
                print(f"  Would update: {objective_id}")
                stats["updated"] += 1

        # Fetch key results for this objective
        print(f"  Fetching key results for objective {obj_pos + 1}...")
        key_results = fetch_key_results(token, objective_id)

        # Validate minimum counts
        if len(key_results) < MIN_KEY_RESULTS_PER_OBJECTIVE:
            print(f"  Warning: Found only {len(key_results)} key results (expected at least {MIN_KEY_RESULTS_PER_OBJECTIVE})")

        # Process key results
        for kr_mapping in obj_mapping.get("keyResults", []):
            kr_pos = kr_mapping.get("position", 0) - 1
            kr_new_name = kr_mapping.get("newName", "")

            if kr_pos < 0 or kr_pos >= len(key_results):
                print(f"\n  [Key Result position {kr_pos + 1}] Position out of range (have {len(key_results)} key results)")
                stats["out_of_range"] += 1
                continue

            kr = key_results[kr_pos]
            kr_id = kr.get("id")
            kr_current_name = get_entity_name(kr)

            if kr_new_name:
                print(f"\n  [Key Result {kr_pos + 1}] '{kr_current_name}' -> '{kr_new_name}'")
                if kr_current_name == kr_new_name:
                    print("    Skipped: Names are identical")
                    stats["skipped"] += 1
                elif apply:
                    if update_key_result(token, kr_id, kr_new_name):
                        print(f"    Updated: {kr_id}")
                        stats["updated"] += 1
                    else:
                        print(f"    Error: Failed to update {kr_id}")
                        stats["errors"] += 1
                else:
                    print(f"    Would update: {kr_id}")
                    stats["updated"] += 1

    return stats


def process_initiatives(
    mapping: Dict[str, Any],
    initiatives: List[Dict[str, Any]],
    token: str,
    apply: bool,
) -> Dict[str, int]:
    """Process initiatives as a flat global list by position."""
    stats = {
        "updated": 0,
        "skipped": 0,
        "missing": 0,
        "out_of_range": 0,
        "errors": 0,
    }

    for init_mapping in mapping.get("initiatives", []):
        init_pos = init_mapping.get("position", 0) - 1  # Convert to 0-indexed
        init_new_name = init_mapping.get("newName", "")

        if init_pos < 0 or init_pos >= len(initiatives):
            print(f"\n[Initiative position {init_pos + 1}] Position out of range (have {len(initiatives)} initiatives)")
            stats["out_of_range"] += 1
            continue

        initiative = initiatives[init_pos]
        initiative_id = initiative.get("id")
        initiative_current_name = get_entity_name(initiative)

        if init_new_name:
            print(f"\n[Initiative {init_pos + 1}] '{initiative_current_name}' -> '{init_new_name}'")
            if initiative_current_name == init_new_name:
                print("  Skipped: Names are identical")
                stats["skipped"] += 1
            elif apply:
                if update_initiative(token, initiative_id, init_new_name):
                    print(f"  Updated: {initiative_id}")
                    stats["updated"] += 1
                else:
                    print(f"  Error: Failed to update {initiative_id}")
                    stats["errors"] += 1
            else:
                print(f"  Would update: {initiative_id}")
                stats["updated"] += 1

    return stats


def merge_stats(stats1: Dict[str, int], stats2: Dict[str, int]) -> Dict[str, int]:
    """Merge two stats dictionaries."""
    return {key: stats1.get(key, 0) + stats2.get(key, 0) for key in stats1}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rename Productboard strategic entities based on hierarchical position."
    )
    parser.add_argument("mapping_file", help="Path to the JSON strategy mapping file")
    group = parser.add_mutually_exclusive_group(required=True)
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
    print(f"Mode: {'APPLY' if args.apply else 'DRY-RUN'}")
    print("-" * 60)

    # Fetch objectives
    print("Fetching objectives from Productboard...")
    objectives = fetch_objectives(token)
    print(f"  Found {len(objectives)} objectives")

    # Fetch initiatives (global list)
    print("Fetching initiatives from Productboard...")
    initiatives = fetch_initiatives(token)
    print(f"  Found {len(initiatives)} initiatives")

    if args.debug:
        if objectives:
            print("\n[DEBUG] Sample objective structure:")
            print(json.dumps(objectives[0], indent=2, default=str)[:1000])
        if initiatives:
            print("\n[DEBUG] Sample initiative structure:")
            print(json.dumps(initiatives[0], indent=2, default=str)[:1000])

    # Validate minimum counts
    if len(objectives) < MIN_OBJECTIVES:
        print(f"\nError: Found only {len(objectives)} objectives. Expected at least {MIN_OBJECTIVES}.", file=sys.stderr)
        sys.exit(1)

    if len(initiatives) < MIN_INITIATIVES:
        print(f"\nWarning: Found only {len(initiatives)} initiatives. Expected at least {MIN_INITIATIVES}.")

    print("-" * 60)
    print("Processing objectives and key results...")

    stats = process_objectives_and_key_results(mapping, objectives, token, args.apply)

    print("\n" + "-" * 60)
    print("Processing initiatives...")

    init_stats = process_initiatives(mapping, initiatives, token, args.apply)
    stats = merge_stats(stats, init_stats)

    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Updated:      {stats['updated']}")
    print(f"  Skipped:      {stats['skipped']}")
    print(f"  Missing:      {stats['missing']}")
    print(f"  Out of range: {stats['out_of_range']}")
    print(f"  Errors:       {stats['errors']}")

    if not args.apply and stats["updated"] > 0:
        print("\nThis was a dry-run. Use --apply to execute updates.")


if __name__ == "__main__":
    main()

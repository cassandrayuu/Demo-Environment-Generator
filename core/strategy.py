"""
Strategy operations.

Handles renaming objectives, key results, and initiatives.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .models import StepResult, StepStatus, StrategyMapping
from .pb_client import ProductboardClient, ProductboardError, default_client


@dataclass
class StrategyEntity:
    """An entity in the strategy hierarchy."""

    id: str
    name: str
    entity_type: str  # 'objective', 'key_result', 'initiative'


@dataclass
class StrategyHierarchy:
    """Complete strategy hierarchy."""

    objectives: List[StrategyEntity]
    key_results_by_objective: Dict[str, List[StrategyEntity]]
    initiatives: List[StrategyEntity]


def _get_entity_name(entity: Dict[str, Any]) -> str:
    """Extract name from entity."""
    return entity.get("name", "") or ""


def build_strategy_hierarchy(
    token: str,
    client: Optional[ProductboardClient] = None,
    logs: Optional[List[str]] = None,
) -> StrategyHierarchy:
    """
    Build the complete strategy hierarchy.

    Fetches objectives, key results, and initiatives.
    """
    client = client or default_client
    logs = logs if logs is not None else []

    logs.append("Fetching strategy from Productboard...")

    # Fetch objectives
    objectives_raw = client.fetch_objectives(token)
    logs.append(f"Found {len(objectives_raw)} objectives")

    # Fetch initiatives
    initiatives_raw = client.fetch_initiatives(token)
    logs.append(f"Found {len(initiatives_raw)} initiatives")

    # Build objectives list (sorted by name)
    objectives_raw.sort(key=lambda o: _get_entity_name(o).lower())
    objectives = [
        StrategyEntity(
            id=o.get("id"),
            name=_get_entity_name(o),
            entity_type="objective",
        )
        for o in objectives_raw
    ]

    # Fetch key results for each objective
    key_results_by_objective: Dict[str, List[StrategyEntity]] = {}
    for obj in objectives_raw:
        obj_id = obj.get("id")
        kr_raw = client.fetch_key_results(token, obj_id)

        # Sort by name
        kr_raw.sort(key=lambda kr: _get_entity_name(kr).lower())

        key_results_by_objective[obj_id] = [
            StrategyEntity(
                id=kr.get("id"),
                name=_get_entity_name(kr),
                entity_type="key_result",
            )
            for kr in kr_raw
        ]

    # Build initiatives list (sorted by name)
    initiatives_raw.sort(key=lambda i: _get_entity_name(i).lower())
    initiatives = [
        StrategyEntity(
            id=i.get("id"),
            name=_get_entity_name(i),
            entity_type="initiative",
        )
        for i in initiatives_raw
    ]

    return StrategyHierarchy(
        objectives=objectives,
        key_results_by_objective=key_results_by_objective,
        initiatives=initiatives,
    )


def rename_strategy(
    token: str,
    mapping: StrategyMapping,
    apply: bool = False,
    client: Optional[ProductboardClient] = None,
) -> StepResult:
    """
    Rename objectives, key results, and initiatives based on mapping.

    Args:
        token: Productboard API token
        mapping: StrategyMapping with new names
        apply: If True, actually apply changes; if False, dry-run
        client: Optional ProductboardClient instance

    Returns:
        StepResult with summary and logs
    """
    client = client or default_client
    logs: List[str] = []
    stats = {"updated": 0, "skipped": 0, "errors": 0, "out_of_range": 0}

    try:
        # Build strategy hierarchy
        hierarchy = build_strategy_hierarchy(token, client, logs)

        mode_str = "APPLY" if apply else "DRY-RUN"
        logs.append(f"Processing strategy rename ({mode_str} mode)...")

        # Process objectives and key results
        logs.append("Processing objectives and key results...")

        for obj_mapping in mapping.objectives:
            obj_pos = obj_mapping.position - 1  # Convert to 0-indexed

            if obj_pos < 0 or obj_pos >= len(hierarchy.objectives):
                logs.append(
                    f"[Objective {obj_pos + 1}] Position out of range (have {len(hierarchy.objectives)})"
                )
                stats["out_of_range"] += 1
                continue

            objective = hierarchy.objectives[obj_pos]

            # Rename objective
            if obj_mapping.new_name:
                if objective.name == obj_mapping.new_name:
                    logs.append(f"[Objective] '{objective.name}' - Skipped (names identical)")
                    stats["skipped"] += 1
                elif apply:
                    try:
                        if client.update_objective(token, objective.id, obj_mapping.new_name):
                            logs.append(
                                f"[Objective] '{objective.name}' -> '{obj_mapping.new_name}' - Updated"
                            )
                            stats["updated"] += 1
                        else:
                            logs.append(
                                f"[Objective] '{objective.name}' -> '{obj_mapping.new_name}' - Failed"
                            )
                            stats["errors"] += 1
                    except ProductboardError as e:
                        logs.append(f"[Objective] '{objective.name}' - Error: {e}")
                        stats["errors"] += 1
                else:
                    logs.append(
                        f"[Objective] '{objective.name}' -> '{obj_mapping.new_name}' - Would update"
                    )
                    stats["updated"] += 1

            # Process key results for this objective
            key_results = hierarchy.key_results_by_objective.get(objective.id, [])

            for kr_mapping in obj_mapping.key_results:
                kr_pos = kr_mapping.position - 1  # Convert to 0-indexed

                if kr_pos < 0 or kr_pos >= len(key_results):
                    logs.append(
                        f"  [Key Result {kr_pos + 1}] Position out of range (have {len(key_results)})"
                    )
                    stats["out_of_range"] += 1
                    continue

                key_result = key_results[kr_pos]

                if kr_mapping.new_name:
                    if key_result.name == kr_mapping.new_name:
                        logs.append(
                            f"  [Key Result] '{key_result.name}' - Skipped (names identical)"
                        )
                        stats["skipped"] += 1
                    elif apply:
                        try:
                            if client.update_key_result(
                                token, key_result.id, kr_mapping.new_name
                            ):
                                logs.append(
                                    f"  [Key Result] '{key_result.name}' -> '{kr_mapping.new_name}' - Updated"
                                )
                                stats["updated"] += 1
                            else:
                                logs.append(
                                    f"  [Key Result] '{key_result.name}' -> '{kr_mapping.new_name}' - Failed"
                                )
                                stats["errors"] += 1
                        except ProductboardError as e:
                            logs.append(f"  [Key Result] '{key_result.name}' - Error: {e}")
                            stats["errors"] += 1
                    else:
                        logs.append(
                            f"  [Key Result] '{key_result.name}' -> '{kr_mapping.new_name}' - Would update"
                        )
                        stats["updated"] += 1

        # Process initiatives
        logs.append("Processing initiatives...")

        for init_mapping in mapping.initiatives:
            init_pos = init_mapping.position - 1  # Convert to 0-indexed

            if init_pos < 0 or init_pos >= len(hierarchy.initiatives):
                logs.append(
                    f"[Initiative {init_pos + 1}] Position out of range (have {len(hierarchy.initiatives)})"
                )
                stats["out_of_range"] += 1
                continue

            initiative = hierarchy.initiatives[init_pos]

            if init_mapping.new_name:
                if initiative.name == init_mapping.new_name:
                    logs.append(
                        f"[Initiative] '{initiative.name}' - Skipped (names identical)"
                    )
                    stats["skipped"] += 1
                elif apply:
                    try:
                        if client.update_initiative(
                            token, initiative.id, init_mapping.new_name
                        ):
                            logs.append(
                                f"[Initiative] '{initiative.name}' -> '{init_mapping.new_name}' - Updated"
                            )
                            stats["updated"] += 1
                        else:
                            logs.append(
                                f"[Initiative] '{initiative.name}' -> '{init_mapping.new_name}' - Failed"
                            )
                            stats["errors"] += 1
                    except ProductboardError as e:
                        logs.append(f"[Initiative] '{initiative.name}' - Error: {e}")
                        stats["errors"] += 1
                else:
                    logs.append(
                        f"[Initiative] '{initiative.name}' -> '{init_mapping.new_name}' - Would update"
                    )
                    stats["updated"] += 1

        # Determine status
        status = StepStatus.SUCCESS if stats["errors"] == 0 else StepStatus.ERROR

        return StepResult(
            name="rename_strategy",
            status=status,
            summary=stats,
            logs=logs,
            error=f"{stats['errors']} errors occurred" if stats["errors"] > 0 else None,
        )

    except ProductboardError as e:
        return StepResult(
            name="rename_strategy",
            status=StepStatus.ERROR,
            summary=stats,
            logs=logs,
            error=str(e),
        )

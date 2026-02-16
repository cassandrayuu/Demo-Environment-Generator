#!/usr/bin/env python3
"""
Productboard POC Setup Orchestrator

Orchestrates all three Productboard setup scripts in one command:
1. pb_rename_hierarchy.py - Updates product/component/feature hierarchy
2. pb_rename_strategy.py - Updates objectives/key results/initiatives
3. pb_generate_insights.py - Creates 5 notes tagged with company name
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def normalize_company_name(company: str) -> str:
    """Normalize company name for filenames (lowercase, underscores)."""
    return company.lower().replace(" ", "_").replace("-", "_")


def check_pb_token() -> bool:
    """Check if PB_TOKEN environment variable is set."""
    token = os.environ.get("PB_TOKEN")
    if not token:
        print("Error: PB_TOKEN environment variable is not set", file=sys.stderr)
        print("Please set it with: export PB_TOKEN='your-token'", file=sys.stderr)
        return False
    return True


def get_file_paths(company: str, base_dir: Path) -> dict:
    """Determine file paths based on company name."""
    normalized = normalize_company_name(company)

    return {
        "mapping_json": base_dir / "product hierarchy mapping files" / f"{normalized}_mapping.json",
        "strategy_json": base_dir / "strategic hierarchy mapping files" / f"{normalized}_strategy_mapping.json",
        "features_txt": base_dir / f"{normalized}_features.txt"
    }


def verify_files_exist(file_paths: dict) -> bool:
    """Verify all required files exist."""
    all_exist = True

    for name, path in file_paths.items():
        if not path.exists():
            print(f"Error: Missing required file: {path}", file=sys.stderr)
            all_exist = False
        else:
            print(f"  Found: {path}")

    return all_exist


def run_step(step_name: str, command: list[str]) -> bool:
    """Run a subprocess command and return success status."""
    print(f"\n{'=' * 60}")
    print(f"Running {step_name}...")
    print(f"Command: {' '.join(command)}")
    print("=" * 60)

    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=False
        )

        if result.returncode != 0:
            print(f"\nError: {step_name} failed with exit code {result.returncode}", file=sys.stderr)
            return False

        return True

    except FileNotFoundError as e:
        print(f"\nError: Could not find script - {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"\nError: {step_name} failed - {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Orchestrate Productboard POC setup (hierarchy, strategy, and insights)"
    )
    parser.add_argument(
        "--company",
        required=True,
        help="Company name (e.g., 'Ottimate')"
    )
    parser.add_argument(
        "--website",
        required=True,
        help="Company website URL (e.g., 'https://ottimate.com')"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Preview changes without applying (default)"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually apply changes via API"
    )

    args = parser.parse_args()

    # Default to dry-run if neither specified
    mode_flag = "--apply" if args.apply else "--dry-run"
    mode_name = "APPLY" if args.apply else "DRY-RUN"

    print("=" * 60)
    print(f"Productboard POC Setup - {mode_name} MODE")
    print("=" * 60)
    print(f"Company: {args.company}")
    print(f"Website: {args.website}")
    print(f"Mode: {mode_name}")

    # Fail fast if PB_TOKEN is missing
    print("\nChecking PB_TOKEN...")
    if not check_pb_token():
        sys.exit(1)
    print("  PB_TOKEN is set")

    # Determine file paths
    base_dir = Path(__file__).parent.resolve()
    file_paths = get_file_paths(args.company, base_dir)

    print("\nVerifying required files...")
    if not verify_files_exist(file_paths):
        print("\nError: One or more required files are missing. Aborting.", file=sys.stderr)
        sys.exit(1)

    # Track step results
    steps_completed = []
    steps_failed = []

    # Step A: Run pb_rename_hierarchy.py
    step_a_cmd = [
        "python3",
        str(base_dir / "pb_rename_hierarchy.py"),
        str(file_paths["mapping_json"]),
        mode_flag
    ]

    if run_step("Step A: Product Hierarchy Rename", step_a_cmd):
        steps_completed.append("Step A: Product Hierarchy Rename")
    else:
        steps_failed.append("Step A: Product Hierarchy Rename")
        print("\nStopping due to Step A failure.", file=sys.stderr)
        print_summary(steps_completed, steps_failed)
        sys.exit(1)

    # Step B: Run pb_rename_strategy.py
    step_b_cmd = [
        "python3",
        str(base_dir / "pb_rename_strategy.py"),
        str(file_paths["strategy_json"]),
        mode_flag
    ]

    if run_step("Step B: Strategic Hierarchy Rename", step_b_cmd):
        steps_completed.append("Step B: Strategic Hierarchy Rename")
    else:
        steps_failed.append("Step B: Strategic Hierarchy Rename")
        print("\nStopping due to Step B failure.", file=sys.stderr)
        print_summary(steps_completed, steps_failed)
        sys.exit(1)

    # Step C: Run pb_generate_insights.py
    step_c_cmd = [
        "python3",
        str(base_dir / "pb_generate_insights.py"),
        "--company", args.company,
        "--features", str(file_paths["features_txt"]),
        mode_flag
    ]

    if run_step("Step C: Generate User Insights", step_c_cmd):
        steps_completed.append("Step C: Generate User Insights")
    else:
        steps_failed.append("Step C: Generate User Insights")
        print("\nStopping due to Step C failure.", file=sys.stderr)
        print_summary(steps_completed, steps_failed)
        sys.exit(1)

    # Final summary
    print_summary(steps_completed, steps_failed)
    print(f"\nPOC setup completed successfully in {mode_name} mode!")


def print_summary(completed: list[str], failed: list[str]):
    """Print final summary of step results."""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if completed:
        print("\nCompleted steps:")
        for step in completed:
            print(f"  [OK] {step}")

    if failed:
        print("\nFailed steps:")
        for step in failed:
            print(f"  [FAILED] {step}")


if __name__ == "__main__":
    main()

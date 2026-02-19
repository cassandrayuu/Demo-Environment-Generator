#!/bin/bash
# =============================================================================
# DoorDash POC Setup Script
# =============================================================================
# This script runs the Productboard POC setup for DoorDash.
#
# Prerequisites:
#   1. Set the PB_TOKEN environment variable:
#      export PB_TOKEN='your-productboard-api-token'
#
#   2. Ensure Python 3 is installed and dependencies are available:
#      pip install requests
#
# Usage:
#   ./run_doordash_poc.sh           # Dry-run mode (preview only)
#   ./run_doordash_poc.sh --apply   # Apply changes to Productboard
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check for PB_TOKEN
if [ -z "$PB_TOKEN" ]; then
    echo "ERROR: PB_TOKEN environment variable is not set."
    echo "Please set it with: export PB_TOKEN='your-token'"
    exit 1
fi

# Parse arguments
MODE="--dry-run"
if [ "$1" == "--apply" ]; then
    MODE="--apply"
    echo "=============================================="
    echo "   APPLY MODE - Changes will be made to PB"
    echo "=============================================="
else
    echo "=============================================="
    echo "   DRY-RUN MODE - Preview only"
    echo "=============================================="
fi

echo ""
echo "Company: DoorDash"
echo "Website: https://doordash.com"
echo ""

# Run the orchestrator
python3 pb_poc_setup.py \
    --company "DoorDash" \
    --website "https://doordash.com" \
    $MODE

echo ""
echo "=============================================="
echo "   DoorDash POC setup complete!"
echo "=============================================="

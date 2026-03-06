# Productboard Demo Environment Generator

## What This Project Does

Automates Productboard demo setup for sales POCs. Takes company info + mapping files → renames product hierarchies, strategic objectives, and generates user feedback insights via the Productboard API.

**Core workflow**: Generate files for a prospect → Select products → Preview changes → Apply to Productboard space.

## Architecture

Three-stage pipeline orchestrated by `pb_poc_setup.py`:

| Stage | Script | What it does |
| --- | --- | --- |
| A | `pb_rename_hierarchy.py` | Renames products, components, features by position |
| B | `pb_rename_strategy.py` | Renames objectives, key results, initiatives |
| C | `pb_generate_insights.py` | Creates 5 realistic user feedback notes |

## Key Files

```
├── pb_poc_setup.py           # Orchestrator - runs stages A→B→C
├── pb_rename_hierarchy.py    # Product hierarchy rename (634 lines)
├── pb_rename_strategy.py     # Strategy hierarchy rename (427 lines)
├── pb_generate_insights.py   # Feedback note generator (465 lines)
├── prospects/
│   ├── _templates/           # Templates for new prospects
│   └── <company>/            # Company-specific mapping files
│       ├── product_mapping.json
│       ├── strategy_mapping.json
│       └── features.txt
└── requirements.txt          # Just: requests>=2.28.0
```

## Mapping File Constraints

**CRITICAL**: Files must match these exact structures or scripts will fail.

### product_mapping.json
- **2 products** total
- **3 components** per product
- **4 features** per component
- Uses position-based mapping (not names)

### strategy_mapping.json
- **3 objectives** with **2 key results** each
- **6 initiatives** total

### features.txt
- One feature name per line (10-25 recommended)
- Used for randomizing feedback in generated insights

## Common Commands

```bash
# Setup
source venv/bin/activate
export PB_TOKEN="your-token"

# Generate files (ask Claude in Nimbalyst):
# "Generate POC files for [Company] [website.com]"

# Select products (when space has different products)
python3 pb_rename_hierarchy.py "prospects/<company>/product_mapping.json" --select

# Preview all changes
python3 pb_poc_setup.py --company "Company" --website "https://company.com" --dry-run

# Apply changes
python3 pb_poc_setup.py --company "Company" --website "https://company.com" --apply
```

## Code Patterns

- **Position-based mapping**: Maps use positions (1-indexed), not entity names
- **Dry-run by default**: All scripts support `--dry-run` and `--apply`
- **API resilience**: Exponential backoff retry (5 attempts) for rate limits/errors
- **Selection persistence**: Saved to `.product_mapping_selection.json` in prospect folder

## Troubleshooting

| Error | Fix |
| --- | --- |
| "No module named 'requests'" | `source venv/bin/activate` |
| "PB_TOKEN not set" | `export PB_TOKEN="your-token"` |
| "Position out of range" | Use `--select` to choose products that match your space |
| API rate limiting | Scripts auto-retry; wait if persistent |

## Development Notes

- **Python 3.7+** required (type hints, f-strings)
- **No test files** - dry-run mode serves as integration test
- **Print-based logging** - no log files generated
- All scripts use `sys.exit(1)` for fatal errors, continue on non-fatal failures

## When Modifying This Code

1. Maintain position-based mapping logic - it allows reuse across different spaces
2. Keep dry-run/apply pattern for all API operations
3. Update README.md if changing file formats or workflows
4. Test with `--dry-run` before applying to real spaces

# Productboard Demo Environment Generator

Generate and apply best-practice demo hierarchies for prospect companies in Productboard. Simply provide a company name and website, and AI generates both product and strategic hierarchies tailored to that company.

## Quick Start (For Your Team)

**One-step generation:** Open this project in Nimbalyst and tell Claude:

> "Generate hierarchies for [Company Name] [website.com]"

Claude will:
1. Research the company's products, market, and strategy
2. Generate a product hierarchy (2 products, 3 components each, 4 features each)
3. Generate a strategic hierarchy (3 objectives, 2 key results each, 6 initiatives)
4. Save both mapping files ready to apply

**Example:**
> "Generate hierarchies for Stripe stripe.com"

## Prerequisites

- Python 3
- A Productboard API token with write access
- The `requests` library (included in the virtual environment)
- Nimbalyst with Claude for hierarchy generation

## Setup

1. Open Terminal and navigate to the project:
```bash
cd /Users/cassandrayuu/hierarchy_sync_project
```

2. Activate the virtual environment:
```bash
source .venv/bin/activate
```

3. Set your Productboard API token:
```bash
export PB_TOKEN="your-productboard-api-token"
```

## Workflow

### Step 1: Generate Mapping Files

In Nimbalyst, ask Claude:
> "Generate hierarchies for [Prospect Name] [website.com]"

This creates two files:
- `product hierarchy mapping files/<company>_mapping.json`
- `strategic hierarchy mapping files/<company>_strategy_mapping.json`

### Step 2: Preview Changes (Dry Run)

Always run a dry-run first:

```bash
# Product hierarchy
python3 pb_rename_hierarchy.py "product hierarchy mapping files/<company>_mapping.json" --dry-run

# Strategic hierarchy
python3 pb_rename_strategy.py "strategic hierarchy mapping files/<company>_strategy_mapping.json" --dry-run
```

### Step 3: Apply Changes

Once verified:

```bash
# Product hierarchy
python3 pb_rename_hierarchy.py "product hierarchy mapping files/<company>_mapping.json" --apply

# Strategic hierarchy
python3 pb_rename_strategy.py "strategic hierarchy mapping files/<company>_strategy_mapping.json" --apply
```

## JSON Mapping File Formats

### Product Hierarchy (`<company>_mapping.json`)

```json
{
  "customer": "CompanyName",
  "hierarchy": [
    {
      "position": 1,
      "newName": "Product Name",
      "components": [
        {
          "position": 1,
          "newName": "Component Name",
          "features": [
            { "position": 1, "newName": "Feature Name" }
          ]
        }
      ]
    }
  ]
}
```

### Strategic Hierarchy (`<company>_strategy_mapping.json`)

```json
{
  "customer": "CompanyName",
  "objectives": [
    {
      "position": 1,
      "newName": "Objective Name",
      "keyResults": [
        {"position": 1, "newName": "Key Result 1"},
        {"position": 2, "newName": "Key Result 2"}
      ]
    }
  ],
  "initiatives": [
    {"position": 1, "newName": "Initiative 1"},
    {"position": 2, "newName": "Initiative 2"},
    {"position": 3, "newName": "Initiative 3"},
    {"position": 4, "newName": "Initiative 4"},
    {"position": 5, "newName": "Initiative 5"},
    {"position": 6, "newName": "Initiative 6"}
  ]
}
```

**Note:** Initiatives are a flat global list (not nested under objectives) because Productboard's API treats initiatives as independent entities that can link to multiple objectives.

## Troubleshooting

### "No module named 'requests'"
```bash
source .venv/bin/activate
```

### "PB_TOKEN environment variable is not set"
```bash
export PB_TOKEN="your-token"
```

### "Position out of range"
The mapping file expects more entities than exist in Productboard. Verify the entity count matches your workspace configuration.

## File Structure

```
hierarchy_sync_project/
├── pb_rename_hierarchy.py          # Product hierarchy rename script
├── pb_rename_strategy.py           # Strategic hierarchy rename script
├── product hierarchy mapping files/
│   ├── mapping_template.json       # Template for product hierarchies
│   ├── exterro_mapping.json
│   ├── ottimate_mapping.json
│   └── productboard_mapping.json
└── strategic hierarchy mapping files/
    ├── strategy_mapping_template.json  # Template for strategic hierarchies
    ├── exterro_strategy_mapping.json
    ├── ottimate_strategy_mapping.json
    └── productboard_strategy_mapping.json
```

# Productboard Demo Environment Generator

Generate and apply best-practice demo hierarchies for prospect companies in Productboard. Simply provide a company name and website, and AI generates product hierarchies, strategic hierarchies, and user insights tailored to that company.

## Quick Start

### 1. One-Time Setup

```bash
# Navigate to project
cd ~/hierarchy_sync_project

# Activate virtual environment
source venv/bin/activate

# Set your Productboard API token
export PB_TOKEN="your-productboard-api-token"
```

### 2. Generate Files for a New Company

In Nimbalyst, ask Claude:
> "Generate hierarchies for [Company Name] [website.com]"

This creates three files:
- `product hierarchy mapping files/<company>_mapping.json`
- `strategic hierarchy mapping files/<company>_strategy_mapping.json`
- `insights mapping files/<company>_features.txt`

### 3. Select Which Products to Rename

Since each Productboard space may have different products, you need to select which ones to rename:

```bash
python3 pb_rename_hierarchy.py "product hierarchy mapping files/<company>_mapping.json" --select
```

This shows your space's products and lets you choose which to rename:
```bash
cd ~/hierarchy_sync_project
source venv/bin/activate
pip install requests
```

### 4. Run the POC Setup

**Dry run (preview changes):**
```bash
python3 pb_poc_setup.py --company "<Company Name>" --website "<website.com>" --dry-run
```

**Apply changes:**
```bash
python3 pb_poc_setup.py --company "<Company Name>" --website "<website.com>" --apply
```

The orchestrator runs three steps:
1. **Step A:** Renames product hierarchy (products, components, features)
2. **Step B:** Renames strategic hierarchy (objectives, key results, initiatives)
3. **Step C:** Generates user insights (5 notes tagged with company name)

---

## Complete Workflow Example

```bash
# 1. Setup
cd ~/hierarchy_sync_project
source venv/bin/activate
export PB_TOKEN="your-token"

# 2. Generate files (in Nimbalyst)
# Ask Claude: "Generate POC files for HL Agency https://hl.agency"

# 3. Select products for your space
python3 pb_rename_hierarchy.py "product hierarchy mapping files/hl_agency_mapping.json" --select
# Enter: 1,3 (or whichever products fit your space)

# 4. Preview changes
python3 pb_poc_setup.py --company "HL Agency" --website "https://hl.agency" --dry-run

# 5. Apply changes
python3 pb_poc_setup.py --company "HL Agency" --website "https://hl.agency" --apply
```

---

## Running Individual Scripts

You can also run each script separately:

### Product Hierarchy
```bash
# Preview
python3 pb_rename_hierarchy.py "product hierarchy mapping files/<company>_mapping.json" --dry-run

# Apply
python3 pb_rename_hierarchy.py "product hierarchy mapping files/<company>_mapping.json" --apply
```

### Strategic Hierarchy
```bash
# Preview
python3 pb_rename_strategy.py "strategic hierarchy mapping files/<company>_strategy_mapping.json" --dry-run

# Apply
python3 pb_rename_strategy.py "strategic hierarchy mapping files/<company>_strategy_mapping.json" --apply
```

### User Insights
```bash
# Preview
python3 pb_generate_insights.py --company "<Company>" --features "insights mapping files/<company>_features.txt" --dry-run

# Apply
python3 pb_generate_insights.py --company "<Company>" --features "insights mapping files/<company>_features.txt" --apply
```

---

## File Structure

```
hierarchy_sync_project/
├── pb_poc_setup.py                     # Orchestrator - runs all three steps
├── pb_rename_hierarchy.py              # Product hierarchy rename script
├── pb_rename_strategy.py               # Strategic hierarchy rename script
├── pb_generate_insights.py             # User insights generator
├── venv/                               # Python virtual environment
├── product hierarchy mapping files/
│   ├── mapping_template.json           # Template
│   ├── hl_agency_mapping.json
│   └── ottimate_mapping.json
├── strategic hierarchy mapping files/
│   ├── strategy_mapping_template.json  # Template
│   ├── hl_agency_strategy_mapping.json
│   └── ottimate_strategy_mapping.json
└── insights mapping files/
    ├── hl_agency_features.txt
    └── ottimate_features.txt
```

---

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
            { "position": 1, "newName": "Feature Name" },
            { "position": 2, "newName": "Feature Name" }
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
    {"position": 2, "newName": "Initiative 2"}
  ]
}
```

### Features List (`<company>_features.txt`)

One feature name per line:
```
Market Research & Insights
Brand Positioning Framework
Creative Brief Builder
```

---

## Troubleshooting

### "No module named 'requests'"
```bash
source venv/bin/activate
```

### "PB_TOKEN environment variable is not set"
```bash
export PB_TOKEN="your-token"
```

### "Position out of range"
Your space has fewer products/components than the mapping expects. Use `--select` to choose which products to rename.

### "This environment is externally managed"
You need to use the virtual environment:
```
Your space has 3 products:
--------------------------------------------------
  1. Privacy & Information Governance (3 components)
  2. test product (1 component)
  3. eDiscovery Platform (3 components)
--------------------------------------------------

Mapping needs 2 products.

Select 2 products to rename (e.g., "1,3" or "1 3"):
> 1,3

✓ Selection saved.
```

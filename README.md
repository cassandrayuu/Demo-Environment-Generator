# Productboard Demo Environment Generator

Generate and apply best-practice demo hierarchies for prospect companies in Productboard. Simply provide a company name and website, and AI generates product hierarchies, strategic hierarchies, and user insights tailored to that company.

## Quick Start

### 1. One-Time Setup

```bash
# Navigate to project
cd ~/Workspace/hierarchy_sync_project

# Activate virtual environment
source venv/bin/activate

# Set your Productboard API token
export PB_TOKEN="your-productboard-api-token"
```

### 2. Generate Files for a New Company

In Nimbalyst, ask Claude:
> "Generate POC files for [Company Name] [website.com]"

**IMPORTANT:** All mapping files must have exactly **2 products** with **3 components each** (4 features per component) to match the Productboard demo space structure.

This creates three files in `prospects/<company>/`:
- `product_mapping.json` - 2 products, 3 components each, 4 features per component
- `strategy_mapping.json` - 3 objectives with 2 key results each, 6 initiatives
- `features.txt` - ~20 feature names for insight generation

### 3. Select Which Products to Rename

Since each Productboard space may have different products, you need to select which ones to rename:

```bash
python3 pb_rename_hierarchy.py "prospects/<company>/product_mapping.json" --select
```

This shows your space's products and lets you choose which to rename.

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
cd ~/Workspace/hierarchy_sync_project
source venv/bin/activate
export PB_TOKEN="your-token"

# 2. Generate files (in Nimbalyst)
# Ask Claude: "Generate POC files for Comcast https://comcast.com"

# 3. Select products for your space
python3 pb_rename_hierarchy.py "prospects/comcast/product_mapping.json" --select
# Enter: 1,3 (or whichever products fit your space)

# 4. Preview changes
python3 pb_poc_setup.py --company "Comcast" --website "https://comcast.com" --dry-run

# 5. Apply changes
python3 pb_poc_setup.py --company "Comcast" --website "https://comcast.com" --apply
```

---

## Running Individual Scripts

You can also run each script separately:

### Product Hierarchy
```bash
# Preview
python3 pb_rename_hierarchy.py "prospects/<company>/product_mapping.json" --dry-run

# Apply
python3 pb_rename_hierarchy.py "prospects/<company>/product_mapping.json" --apply
```

### Strategic Hierarchy
```bash
# Preview
python3 pb_rename_strategy.py "prospects/<company>/strategy_mapping.json" --dry-run

# Apply
python3 pb_rename_strategy.py "prospects/<company>/strategy_mapping.json" --apply
```

### User Insights
```bash
# Preview
python3 pb_generate_insights.py --company "<Company>" --features "prospects/<company>/features.txt" --dry-run

# Apply
python3 pb_generate_insights.py --company "<Company>" --features "prospects/<company>/features.txt" --apply
```

---

## File Structure

```
hierarchy_sync_project/
├── pb_poc_setup.py                 # Orchestrator - runs all three steps
├── pb_rename_hierarchy.py          # Product hierarchy rename script
├── pb_rename_strategy.py           # Strategic hierarchy rename script
├── pb_generate_insights.py         # User insights generator
├── venv/                           # Python virtual environment
└── prospects/
    ├── _templates/                 # Template files for new prospects
    │   ├── product_mapping.json
    │   ├── strategy_mapping.json
    │   └── features.txt
    ├── comcast/
    │   ├── product_mapping.json
    │   ├── strategy_mapping.json
    │   └── features.txt
    └── exterro/
        ├── product_mapping.json
        ├── strategy_mapping.json
        └── features.txt
```

---

## JSON Mapping File Formats

### Product Hierarchy (`product_mapping.json`)

**Must have exactly 2 products, 3 components each, 4 features per component.**

```json
{
  "customer": "CompanyName",
  "hierarchy": [
    {
      "position": 1,
      "newName": "Product 1 Name",
      "components": [
        {
          "position": 1,
          "newName": "Component Name",
          "features": [
            { "position": 1, "newName": "Feature 1" },
            { "position": 2, "newName": "Feature 2" },
            { "position": 3, "newName": "Feature 3" },
            { "position": 4, "newName": "Feature 4" }
          ]
        },
        { "position": 2, "newName": "Component 2", "features": [...] },
        { "position": 3, "newName": "Component 3", "features": [...] }
      ]
    },
    {
      "position": 2,
      "newName": "Product 2 Name",
      "components": [...]
    }
  ]
}
```

### Strategic Hierarchy (`strategy_mapping.json`)

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

### Features List (`features.txt`)

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

"""
AI-powered mapping file generator.

Uses LLM APIs (Gemini or Anthropic) to research a company and generate
realistic product, strategy, and feature mappings.
"""

import hashlib
import json
import os
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple

import requests

# LLM Provider configuration defaults
# Note: These are read at runtime in generate_flexible_mappings() to ensure
# Railway env vars are picked up correctly
DEFAULT_LLM_PROVIDER = "gemini"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"

from .models import (
    ComponentMapping,
    FeatureMapping,
    FlexibleOptions,
    InitiativeMapping,
    KeyResultMapping,
    ObjectiveMapping,
    ProductHierarchyMapping,
    ProductMapping,
    ProductStructure,
    RenamePlan,
    StrategyMapping,
)

# Product hierarchy constraints (fixed structure for non-flexible generation)
REQUIRED_PRODUCTS = 2
REQUIRED_COMPONENTS_PER_PRODUCT = 3
REQUIRED_FEATURES_PER_COMPONENT = 4

# Strategy constraints (still fixed for MVP)
REQUIRED_OBJECTIVES = 3
REQUIRED_KEY_RESULTS_PER_OBJECTIVE = 2
REQUIRED_INITIATIVES = 6
REQUIRED_FEATURES_LIST = 20


@dataclass
class GeneratedMappings:
    """Complete set of generated mappings."""

    product_mapping: ProductMapping
    strategy_mapping: StrategyMapping
    features_list: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "productMapping": self.product_mapping.to_dict(),
            "strategyMapping": self.strategy_mapping.to_dict(),
            "features": self.features_list,
        }


class GenerationError(Exception):
    """Error during mapping generation."""

    pass


@dataclass
class WebsiteContext:
    """Context extracted from a website for grounding LLM generation."""

    title: str
    description: str
    content_snippet: str

    def to_prompt_section(self) -> str:
        """Format context for inclusion in prompts."""
        parts = []
        if self.title:
            parts.append(f"Page Title: {self.title}")
        if self.description:
            parts.append(f"Description: {self.description}")
        if self.content_snippet:
            parts.append(f"Content: {self.content_snippet}")
        return "\n".join(parts) if parts else ""


class _HTMLTextExtractor(HTMLParser):
    """Simple HTML parser to extract text content."""

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.title = ""
        self.description = ""
        self._in_title = False
        self._in_script = False
        self._in_style = False

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        elif tag in ("script", "style"):
            self._in_script = True
            self._in_style = True
        elif tag == "meta":
            attrs_dict = dict(attrs)
            if attrs_dict.get("name", "").lower() == "description":
                self.description = attrs_dict.get("content", "")[:300]

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag in ("script", "style"):
            self._in_script = False
            self._in_style = False

    def handle_data(self, data):
        if self._in_title:
            self.title = data.strip()[:200]
        elif not self._in_script and not self._in_style:
            text = data.strip()
            if text and len(text) > 3:
                self.text_parts.append(text)


def fetch_website_context(url: str, timeout: int = 5) -> Optional[WebsiteContext]:
    """
    Fetch and extract context from a website URL.

    Returns None on any failure (timeout, 404, JS-only page, etc.)
    """
    try:
        # Normalize URL
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        print(f"[Generator] Fetching website context from: {url}", flush=True)

        response = requests.get(
            url,
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; ProductboardDemo/1.0)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        response.raise_for_status()

        # Parse HTML
        parser = _HTMLTextExtractor()
        parser.feed(response.text)

        # Build content snippet from extracted text
        content_parts = parser.text_parts[:20]  # First 20 text chunks
        content_snippet = " ".join(content_parts)[:500]  # Limit to 500 chars

        context = WebsiteContext(
            title=parser.title,
            description=parser.description,
            content_snippet=content_snippet,
        )

        print(f"[Generator] Extracted context - title: '{context.title[:50]}...'", flush=True)
        return context

    except Exception as e:
        print(f"[Generator] Failed to fetch website context: {e}", flush=True)
        return None


def _get_seed_from_inputs(company: str, website: str) -> int:
    """Generate a deterministic seed from company and website."""
    combined = f"{company.lower().strip()}:{website.lower().strip()}"
    hash_bytes = hashlib.md5(combined.encode()).digest()
    return int.from_bytes(hash_bytes[:4], byteorder="big")


def _normalize_website(website: str) -> str:
    """Normalize website URL to https://."""
    website = website.strip()
    if not website:
        return ""
    if not website.startswith(("http://", "https://")):
        website = f"https://{website}"
    if website.startswith("http://"):
        website = website.replace("http://", "https://", 1)
    return website


def _extract_domain(website: str) -> str:
    """Extract domain from website URL."""
    website = _normalize_website(website)
    # Remove protocol
    domain = re.sub(r"^https?://", "", website)
    # Remove path
    domain = domain.split("/")[0]
    # Remove www
    domain = re.sub(r"^www\.", "", domain)
    return domain


def _build_generation_prompt(company: str, website: str) -> str:
    """Build the prompt for Claude to generate mappings."""
    domain = _extract_domain(website)

    return f"""You are helping create a demo environment for Productboard, a product management tool.
Generate realistic product hierarchy and strategy mappings for a company.

**Company**: {company}
**Website**: {website}
**Domain**: {domain}

## Task

Generate mappings that would make sense for this company's products. The names should be realistic,
specific to the company's industry, and sound like actual product features a company like this would have.

## STRICT Requirements

You MUST generate EXACTLY:
- 2 products
- 3 components per product (6 total)
- 4 features per component (24 total)
- 3 objectives
- 2 key results per objective (6 total)
- 6 initiatives
- 20 feature names for the features list

## Output Format

Return a JSON object with this EXACT structure:

```json
{{
  "products": [
    {{
      "name": "Product Name 1",
      "components": [
        {{
          "name": "Component Name",
          "features": ["Feature 1", "Feature 2", "Feature 3", "Feature 4"]
        }},
        // ... 2 more components with 4 features each
      ]
    }},
    // ... 1 more product with 3 components, 4 features each
  ],
  "objectives": [
    {{
      "name": "Objective Name",
      "keyResults": ["Key Result 1", "Key Result 2"]
    }},
    // ... 2 more objectives with 2 key results each
  ],
  "initiatives": ["Initiative 1", "Initiative 2", "Initiative 3", "Initiative 4", "Initiative 5", "Initiative 6"],
  "featuresList": ["Feature name 1", "Feature name 2", ... ] // 20 feature names
}}
```

## Guidelines

1. **Products**: Name them based on what the company likely offers (e.g., "Analytics Platform", "Customer Portal")
2. **Components**: Logical groupings within each product (e.g., "Dashboard", "Reporting", "Integration Hub")
3. **Features**: Specific capabilities (e.g., "Real-time Data Sync", "Custom Report Builder")
4. **Objectives**: High-level business goals (e.g., "Increase Customer Retention")
5. **Key Results**: Measurable outcomes (e.g., "Reduce churn rate by 15%")
6. **Initiatives**: Strategic projects (e.g., "Launch Self-Service Portal")
7. **Features List**: Mix of the features from products plus some additional ones

Be creative but realistic. Names should sound professional and industry-appropriate.

Return ONLY the JSON object, no other text."""


def _parse_claude_response(response_text: str) -> Dict[str, Any]:
    """Parse Claude's JSON response, handling code blocks."""
    # Try to extract JSON from code blocks first
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response_text)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_str = response_text.strip()

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise GenerationError(f"Failed to parse Claude response as JSON: {e}")


def _validate_generated_data(data: Dict[str, Any]) -> List[str]:
    """Validate the generated data meets all requirements. Returns list of errors."""
    errors = []

    # Validate products
    products = data.get("products", [])
    if len(products) != REQUIRED_PRODUCTS:
        errors.append(f"Expected {REQUIRED_PRODUCTS} products, got {len(products)}")

    for i, product in enumerate(products):
        components = product.get("components", [])
        if len(components) != REQUIRED_COMPONENTS_PER_PRODUCT:
            errors.append(
                f"Product {i + 1}: Expected {REQUIRED_COMPONENTS_PER_PRODUCT} components, got {len(components)}"
            )
        for j, component in enumerate(components):
            features = component.get("features", [])
            if len(features) != REQUIRED_FEATURES_PER_COMPONENT:
                errors.append(
                    f"Product {i + 1}, Component {j + 1}: Expected {REQUIRED_FEATURES_PER_COMPONENT} features, got {len(features)}"
                )

    # Validate objectives
    objectives = data.get("objectives", [])
    if len(objectives) != REQUIRED_OBJECTIVES:
        errors.append(f"Expected {REQUIRED_OBJECTIVES} objectives, got {len(objectives)}")

    for i, objective in enumerate(objectives):
        key_results = objective.get("keyResults", [])
        if len(key_results) != REQUIRED_KEY_RESULTS_PER_OBJECTIVE:
            errors.append(
                f"Objective {i + 1}: Expected {REQUIRED_KEY_RESULTS_PER_OBJECTIVE} key results, got {len(key_results)}"
            )

    # Validate initiatives
    initiatives = data.get("initiatives", [])
    if len(initiatives) != REQUIRED_INITIATIVES:
        errors.append(f"Expected {REQUIRED_INITIATIVES} initiatives, got {len(initiatives)}")

    # Validate features list
    features_list = data.get("featuresList", [])
    if len(features_list) < REQUIRED_FEATURES_LIST:
        errors.append(
            f"Expected at least {REQUIRED_FEATURES_LIST} features in list, got {len(features_list)}"
        )

    return errors


def _convert_to_mappings(
    data: Dict[str, Any], company: str
) -> Tuple[ProductMapping, StrategyMapping, List[str]]:
    """Convert parsed data to mapping objects."""
    # Build product mapping
    hierarchy = []
    for i, product in enumerate(data["products"]):
        components = []
        for j, component in enumerate(product["components"]):
            features = [
                FeatureMapping(position=k + 1, new_name=feat)
                for k, feat in enumerate(component["features"])
            ]
            components.append(
                ComponentMapping(
                    position=j + 1, new_name=component["name"], features=features
                )
            )
        hierarchy.append(
            ProductHierarchyMapping(
                position=i + 1, new_name=product["name"], components=components
            )
        )

    product_mapping = ProductMapping(customer=company, hierarchy=hierarchy)

    # Build strategy mapping
    objectives = []
    for i, obj in enumerate(data["objectives"]):
        key_results = [
            KeyResultMapping(position=k + 1, new_name=kr)
            for k, kr in enumerate(obj["keyResults"])
        ]
        objectives.append(
            ObjectiveMapping(position=i + 1, new_name=obj["name"], key_results=key_results)
        )

    initiatives = [
        InitiativeMapping(position=i + 1, new_name=init)
        for i, init in enumerate(data["initiatives"])
    ]

    strategy_mapping = StrategyMapping(
        customer=company, objectives=objectives, initiatives=initiatives
    )

    # Features list
    features_list = data.get("featuresList", [])

    return product_mapping, strategy_mapping, features_list


def generate_mappings(
    company: str,
    website: str,
    anthropic_api_key: Optional[str] = None,
) -> GeneratedMappings:
    """
    Generate product, strategy, and feature mappings for a company.

    Args:
        company: Company name
        website: Company website URL
        anthropic_api_key: Anthropic API key (falls back to ANTHROPIC_API_KEY env var)

    Returns:
        GeneratedMappings with all mapping data

    Raises:
        GenerationError: If generation or validation fails
    """
    # Get API key
    api_key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise GenerationError(
            "Anthropic API key not provided. Set ANTHROPIC_API_KEY environment variable."
        )

    # Normalize inputs
    website = _normalize_website(website)

    # Build prompt
    prompt = _build_generation_prompt(company, website)

    # Call Claude API
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text

    except ImportError:
        raise GenerationError(
            "anthropic package not installed. Run: pip install anthropic"
        )
    except Exception as e:
        raise GenerationError(f"Claude API call failed: {e}")

    # Parse response
    data = _parse_claude_response(response_text)

    # Validate
    errors = _validate_generated_data(data)
    if errors:
        raise GenerationError(f"Generated data validation failed: {'; '.join(errors)}")

    # Convert to mapping objects
    product_mapping, strategy_mapping, features_list = _convert_to_mappings(data, company)

    return GeneratedMappings(
        product_mapping=product_mapping,
        strategy_mapping=strategy_mapping,
        features_list=features_list,
    )


def generate_mappings_from_template(company: str) -> GeneratedMappings:
    """
    Generate mappings using templates (no AI, for testing/fallback).

    This creates generic mappings based on the company name.
    """
    # Generic product hierarchy
    hierarchy = [
        ProductHierarchyMapping(
            position=1,
            new_name=f"{company} Platform",
            components=[
                ComponentMapping(
                    position=1,
                    new_name="Core Engine",
                    features=[
                        FeatureMapping(position=1, new_name="Data Processing"),
                        FeatureMapping(position=2, new_name="API Gateway"),
                        FeatureMapping(position=3, new_name="Authentication"),
                        FeatureMapping(position=4, new_name="User Management"),
                    ],
                ),
                ComponentMapping(
                    position=2,
                    new_name="Analytics Dashboard",
                    features=[
                        FeatureMapping(position=1, new_name="Real-time Metrics"),
                        FeatureMapping(position=2, new_name="Custom Reports"),
                        FeatureMapping(position=3, new_name="Data Export"),
                        FeatureMapping(position=4, new_name="Scheduled Reports"),
                    ],
                ),
                ComponentMapping(
                    position=3,
                    new_name="Integration Hub",
                    features=[
                        FeatureMapping(position=1, new_name="Third-party Connectors"),
                        FeatureMapping(position=2, new_name="Webhook Management"),
                        FeatureMapping(position=3, new_name="Data Sync"),
                        FeatureMapping(position=4, new_name="API Documentation"),
                    ],
                ),
            ],
        ),
        ProductHierarchyMapping(
            position=2,
            new_name=f"{company} Mobile",
            components=[
                ComponentMapping(
                    position=1,
                    new_name="Mobile Core",
                    features=[
                        FeatureMapping(position=1, new_name="Push Notifications"),
                        FeatureMapping(position=2, new_name="Offline Mode"),
                        FeatureMapping(position=3, new_name="Biometric Auth"),
                        FeatureMapping(position=4, new_name="Deep Linking"),
                    ],
                ),
                ComponentMapping(
                    position=2,
                    new_name="Mobile Experience",
                    features=[
                        FeatureMapping(position=1, new_name="Quick Actions"),
                        FeatureMapping(position=2, new_name="Widget Support"),
                        FeatureMapping(position=3, new_name="Dark Mode"),
                        FeatureMapping(position=4, new_name="Accessibility"),
                    ],
                ),
                ComponentMapping(
                    position=3,
                    new_name="Mobile Sync",
                    features=[
                        FeatureMapping(position=1, new_name="Background Sync"),
                        FeatureMapping(position=2, new_name="Conflict Resolution"),
                        FeatureMapping(position=3, new_name="Bandwidth Optimization"),
                        FeatureMapping(position=4, new_name="Selective Sync"),
                    ],
                ),
            ],
        ),
    ]

    product_mapping = ProductMapping(customer=company, hierarchy=hierarchy)

    # Generic strategy
    objectives = [
        ObjectiveMapping(
            position=1,
            new_name="Increase Customer Acquisition",
            key_results=[
                KeyResultMapping(position=1, new_name="Grow new signups by 25%"),
                KeyResultMapping(position=2, new_name="Reduce CAC by 15%"),
            ],
        ),
        ObjectiveMapping(
            position=2,
            new_name="Improve Customer Retention",
            key_results=[
                KeyResultMapping(position=1, new_name="Increase NPS to 50+"),
                KeyResultMapping(position=2, new_name="Reduce churn rate to <5%"),
            ],
        ),
        ObjectiveMapping(
            position=3,
            new_name="Accelerate Product Innovation",
            key_results=[
                KeyResultMapping(position=1, new_name="Launch 3 major features"),
                KeyResultMapping(position=2, new_name="Reduce time-to-market by 20%"),
            ],
        ),
    ]

    initiatives = [
        InitiativeMapping(position=1, new_name="Launch Self-Service Portal"),
        InitiativeMapping(position=2, new_name="Implement AI-Powered Insights"),
        InitiativeMapping(position=3, new_name="Expand Integration Ecosystem"),
        InitiativeMapping(position=4, new_name="Redesign Onboarding Flow"),
        InitiativeMapping(position=5, new_name="Build Enterprise Features"),
        InitiativeMapping(position=6, new_name="Mobile App 2.0"),
    ]

    strategy_mapping = StrategyMapping(
        customer=company, objectives=objectives, initiatives=initiatives
    )

    # Generic features list
    features_list = [
        "Real-time Analytics",
        "Custom Dashboards",
        "API Integration",
        "User Management",
        "Role-based Access",
        "Audit Logging",
        "Data Export",
        "Scheduled Reports",
        "Push Notifications",
        "Email Alerts",
        "Webhook Support",
        "SSO Integration",
        "Two-Factor Auth",
        "Mobile App",
        "Offline Mode",
        "Bulk Operations",
        "Advanced Search",
        "Custom Fields",
        "Workflow Automation",
        "Team Collaboration",
    ]

    return GeneratedMappings(
        product_mapping=product_mapping,
        strategy_mapping=strategy_mapping,
        features_list=features_list,
    )


def _build_flexible_generation_prompt(
    company: str, website: str, structure: List[ProductStructure],
    context: Optional[WebsiteContext] = None
) -> str:
    """Build prompt for flexible mapping generation based on actual structure."""
    domain = _extract_domain(website)

    # Build structure description
    structure_desc = []
    for i, product in enumerate(structure):
        comp_descs = []
        for j, comp in enumerate(product.components):
            comp_descs.append(
                f"    - Component {j+1}: {comp.feature_count} features"
            )
        structure_desc.append(
            f"  Product {i+1} ({product.name}): {len(product.components)} components\n"
            + "\n".join(comp_descs)
        )

    structure_text = "\n".join(structure_desc)

    # Include website context if available
    context_section = ""
    if context:
        context_text = context.to_prompt_section()
        if context_text:
            context_section = f"""
**About this product** (from website):
{context_text}

Use this information to generate accurate, product-specific names and features.
"""

    return f"""You are helping create a demo environment for Productboard, a product management tool.
Generate realistic product hierarchy and strategy mappings for a company.

**Company**: {company}
**Website**: {website}
**Domain**: {domain}
{context_section}
**Existing Structure**:
{structure_text}

## Task

Generate NEW NAMES for the existing hierarchy that would make sense for {company}'s products.
The names should be realistic, specific to the company's industry, and sound like actual product features.
Base your names on what this product ACTUALLY does (see context above), not generic guesses.

Also generate realistic objectives, key results, and initiatives appropriate for {company} and this workspace.

## Output Format

Return a JSON object with EXACTLY this structure (matching the number of products/components/features above):
```json
{{
  "products": [
    {{
      "name": "New Product Name",
      "components": [
        {{
          "name": "New Component Name",
          "features": ["Feature 1", "Feature 2", ...]
        }}
      ]
    }}
  ],
  "objectives": [
    {{
      "name": "Objective Name",
      "keyResults": ["Key Result 1", "Key Result 2"]
    }}
  ],
  "initiatives": ["Initiative 1", ...],
  "featuresList": ["Feature name 1", ...]
}}
```

Be creative but realistic. Names should sound professional and industry-appropriate.
Return ONLY the JSON object, no other text."""


def _validate_flexible_data(
    data: Dict[str, Any], structure: List[ProductStructure]
) -> List[str]:
    """Validate generated data matches the expected structure."""
    errors = []

    products = data.get("products", [])
    if len(products) != len(structure):
        errors.append(
            f"Expected {len(structure)} products, got {len(products)}"
        )
        return errors

    for i, (product, expected) in enumerate(zip(products, structure)):
        # Validate product has required fields
        if "name" not in product:
            errors.append(f"Product {i+1}: Missing 'name' field")
            continue

        components = product.get("components", [])
        if len(components) != len(expected.components):
            errors.append(
                f"Product {i+1}: Expected {len(expected.components)} components, got {len(components)}"
            )
            continue

        for j, (comp, exp_comp) in enumerate(zip(components, expected.components)):
            # Validate component has required fields
            if "name" not in comp:
                errors.append(f"Product {i+1}, Component {j+1}: Missing 'name' field")
                continue

            features = comp.get("features", [])
            if len(features) != exp_comp.feature_count:
                errors.append(
                    f"Product {i+1}, Component {j+1}: Expected {exp_comp.feature_count} features, got {len(features)}"
                )

    # Validate strategy structure (permissive on counts, strict on structure)
    objectives = data.get("objectives", [])
    if not objectives:
        errors.append("No objectives generated")
    for i, obj in enumerate(objectives):
        if "name" not in obj:
            errors.append(f"Objective {i+1}: Missing 'name' field")
        if "keyResults" not in obj or not isinstance(obj.get("keyResults"), list):
            errors.append(f"Objective {i+1}: Missing or invalid 'keyResults' field")

    initiatives = data.get("initiatives", [])
    if not initiatives:
        errors.append("No initiatives generated")

    features_list = data.get("featuresList", [])
    if not features_list:
        errors.append("No features list generated")

    return errors


def _convert_flexible_to_mappings(
    data: Dict[str, Any], company: str
) -> Tuple[ProductMapping, StrategyMapping, List[str]]:
    """Convert flexibly-generated data to mapping objects."""
    # Build product mapping
    hierarchy = []
    for i, product in enumerate(data["products"]):
        components = []
        for j, component in enumerate(product["components"]):
            features = [
                FeatureMapping(position=k + 1, new_name=feat)
                for k, feat in enumerate(component["features"])
            ]
            components.append(
                ComponentMapping(
                    position=j + 1, new_name=component["name"], features=features
                )
            )
        hierarchy.append(
            ProductHierarchyMapping(
                position=i + 1, new_name=product["name"], components=components
            )
        )

    product_mapping = ProductMapping(customer=company, hierarchy=hierarchy)

    # Build strategy mapping (same as before)
    objectives = []
    for i, obj in enumerate(data["objectives"]):
        key_results = [
            KeyResultMapping(position=k + 1, new_name=kr)
            for k, kr in enumerate(obj["keyResults"])
        ]
        objectives.append(
            ObjectiveMapping(position=i + 1, new_name=obj["name"], key_results=key_results)
        )

    initiatives = [
        InitiativeMapping(position=i + 1, new_name=init)
        for i, init in enumerate(data["initiatives"])
    ]

    strategy_mapping = StrategyMapping(
        customer=company, objectives=objectives, initiatives=initiatives
    )

    features_list = data.get("featuresList", [])

    return product_mapping, strategy_mapping, features_list


def _call_gemini(prompt: str, api_key: str, model_name: str = DEFAULT_GEMINI_MODEL) -> str:
    """Call Gemini API, return raw text response."""
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise GenerationError(
            "google-genai package not installed. Run: pip install google-genai"
        )

    try:
        print(f"[Generator] Creating Gemini client...", flush=True)
        client = genai.Client(api_key=api_key)
        print(f"[Generator] Sending request to Gemini...", flush=True)
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        # Handle empty/blocked responses
        text = response.text if response.text else ""
        print(f"[Generator] Gemini response received, length: {len(text)}", flush=True)
        if not text.strip():
            # Check for blocking reasons
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'finish_reason'):
                    print(f"[Generator] Gemini finish_reason: {candidate.finish_reason}", flush=True)
                if hasattr(candidate, 'safety_ratings'):
                    print(f"[Generator] Gemini safety_ratings: {candidate.safety_ratings}", flush=True)
            raise GenerationError("Gemini returned empty response (possibly blocked by safety filters)")
        return text
    except Exception as e:
        print(f"[Generator] Gemini API error: {type(e).__name__}: {e}", flush=True)
        error_str = str(e).lower()
        if "quota" in error_str or "rate" in error_str or "429" in error_str:
            raise GenerationError(f"Gemini rate limit/quota exceeded: {e}")
        elif "permission" in error_str or "401" in error_str or "403" in error_str:
            raise GenerationError(f"Gemini auth error: {e}")
        else:
            raise GenerationError(f"Gemini API call failed: {e}")


def _call_anthropic(prompt: str, api_key: str) -> str:
    """Call Anthropic API, return raw text response."""
    try:
        import anthropic
    except ImportError:
        raise GenerationError(
            "anthropic package not installed. Run: pip install anthropic"
        )

    try:
        print(f"[Generator] Creating Anthropic client...", flush=True)
        client = anthropic.Anthropic(api_key=api_key)
        print(f"[Generator] Sending request to Claude...", flush=True)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=16384,  # Increased for longer outputs (40+ notes)
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text
        print(f"[Generator] Claude response received, length: {len(text)}", flush=True)
        return text
    except Exception as e:
        print(f"[Generator] Claude API error: {type(e).__name__}: {e}", flush=True)
        raise GenerationError(f"Claude API call failed: {e}")


def generate_flexible_mappings(
    company: str,
    website: str,
    structure: List[ProductStructure],
) -> GeneratedMappings:
    """
    Generate mappings that match the actual structure of selected products.

    LLM provider is configured via LLM_PROVIDER env var:
    - "gemini" (default): uses GEMINI_API_KEY
    - "anthropic": uses ANTHROPIC_API_KEY

    Args:
        company: Company name
        website: Company website URL
        structure: Actual structure of selected products

    Returns:
        GeneratedMappings with mappings matching the structure
    """
    website = _normalize_website(website)

    # Fetch website context for grounding (fails gracefully)
    context = fetch_website_context(website)

    prompt = _build_flexible_generation_prompt(company, website, structure, context)

    # Read env vars at runtime (not module load time) to ensure Railway env vars work
    provider = os.environ.get("LLM_PROVIDER", DEFAULT_LLM_PROVIDER).lower()
    gemini_model = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
    print(f"[Generator] Using LLM provider: {provider}", flush=True)

    if provider == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("[Generator] ERROR: GEMINI_API_KEY not set!", flush=True)
            raise GenerationError(
                "GEMINI_API_KEY not set. Set environment variable or switch to LLM_PROVIDER=anthropic."
            )
        print(f"[Generator] Calling Gemini model: {gemini_model}", flush=True)
        print(f"[Generator] API key present: True (length: {len(api_key)})", flush=True)
        print(f"[Generator] About to call _call_gemini...", flush=True)
        try:
            response_text = _call_gemini(prompt, api_key, gemini_model)
            print(f"[Generator] Gemini call completed successfully", flush=True)
        except Exception as e:
            print(f"[Generator] _call_gemini raised exception: {type(e).__name__}: {e}", flush=True)
            raise
    else:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise GenerationError(
                "Anthropic API key not provided. Set ANTHROPIC_API_KEY environment variable."
            )
        print("[Generator] Calling Anthropic Claude", flush=True)
        try:
            response_text = _call_anthropic(prompt, api_key)
            print("[Generator] Anthropic call completed successfully", flush=True)
        except Exception as e:
            print(f"[Generator] Anthropic call failed: {type(e).__name__}: {e}", flush=True)
            raise

    data = _parse_claude_response(response_text)
    print(f"[Generator] Parsed data keys: {list(data.keys())}", flush=True)
    if "products" in data and data["products"]:
        print(f"[Generator] First product keys: {list(data['products'][0].keys()) if data['products'] else 'empty'}", flush=True)
        print(f"[Generator] First product sample: {str(data['products'][0])[:200]}", flush=True)

    errors = _validate_flexible_data(data, structure)
    if errors:
        print(f"[Generator] Validation errors: {errors}", flush=True)
        raise GenerationError(f"Generated data validation failed: {'; '.join(errors)}")

    product_mapping, strategy_mapping, features_list = _convert_flexible_to_mappings(
        data, company
    )

    return GeneratedMappings(
        product_mapping=product_mapping,
        strategy_mapping=strategy_mapping,
        features_list=features_list,
    )


def generate_flexible_mappings_from_template(
    company: str,
    structure: List[ProductStructure],
) -> GeneratedMappings:
    """
    Generate template-based mappings matching actual structure.

    Fallback when AI generation is unavailable.
    """
    # Generic component/feature name pools
    component_names = [
        "Core Engine", "Analytics Dashboard", "Integration Hub",
        "User Portal", "Admin Console", "API Gateway",
        "Reporting Module", "Security Center", "Data Pipeline",
        "Workflow Engine", "Collaboration Hub", "Mobile Backend",
    ]

    feature_names = [
        "Data Processing", "Real-time Sync", "Custom Reports",
        "User Management", "Role-based Access", "API Integration",
        "Push Notifications", "Audit Logging", "Data Export",
        "Scheduled Tasks", "Email Alerts", "Webhook Support",
        "SSO Integration", "Two-Factor Auth", "Bulk Operations",
        "Advanced Search", "Custom Fields", "Workflow Automation",
        "Team Collaboration", "Dashboard Widgets", "Data Visualization",
        "Performance Metrics", "Error Tracking", "Usage Analytics",
    ]

    # Build hierarchy matching structure
    hierarchy = []
    comp_idx = 0
    feat_idx = 0

    for i, product_struct in enumerate(structure):
        components = []
        for j, comp_struct in enumerate(product_struct.components):
            features = []
            for k in range(comp_struct.feature_count):
                feat_name = feature_names[feat_idx % len(feature_names)]
                features.append(FeatureMapping(position=k + 1, new_name=feat_name))
                feat_idx += 1

            comp_name = component_names[comp_idx % len(component_names)]
            components.append(
                ComponentMapping(position=j + 1, new_name=comp_name, features=features)
            )
            comp_idx += 1

        product_name = f"{company} {'Platform' if i == 0 else 'Mobile' if i == 1 else f'Suite {i+1}'}"
        hierarchy.append(
            ProductHierarchyMapping(
                position=i + 1, new_name=product_name, components=components
            )
        )

    product_mapping = ProductMapping(customer=company, hierarchy=hierarchy)

    # Generic strategy (fixed structure)
    objectives = [
        ObjectiveMapping(
            position=1,
            new_name="Increase Customer Acquisition",
            key_results=[
                KeyResultMapping(position=1, new_name="Grow new signups by 25%"),
                KeyResultMapping(position=2, new_name="Reduce CAC by 15%"),
            ],
        ),
        ObjectiveMapping(
            position=2,
            new_name="Improve Customer Retention",
            key_results=[
                KeyResultMapping(position=1, new_name="Increase NPS to 50+"),
                KeyResultMapping(position=2, new_name="Reduce churn rate to <5%"),
            ],
        ),
        ObjectiveMapping(
            position=3,
            new_name="Accelerate Product Innovation",
            key_results=[
                KeyResultMapping(position=1, new_name="Launch 3 major features"),
                KeyResultMapping(position=2, new_name="Reduce time-to-market by 20%"),
            ],
        ),
    ]

    initiatives = [
        InitiativeMapping(position=1, new_name="Launch Self-Service Portal"),
        InitiativeMapping(position=2, new_name="Implement AI-Powered Insights"),
        InitiativeMapping(position=3, new_name="Expand Integration Ecosystem"),
        InitiativeMapping(position=4, new_name="Redesign Onboarding Flow"),
        InitiativeMapping(position=5, new_name="Build Enterprise Features"),
        InitiativeMapping(position=6, new_name="Mobile App 2.0"),
    ]

    strategy_mapping = StrategyMapping(
        customer=company, objectives=objectives, initiatives=initiatives
    )

    features_list = feature_names[:20]

    return GeneratedMappings(
        product_mapping=product_mapping,
        strategy_mapping=strategy_mapping,
        features_list=features_list,
    )


def create_rename_plan(
    structure: List[ProductStructure],
    mappings: GeneratedMappings,
) -> RenamePlan:
    """
    Create a preview plan showing current -> new names.
    """
    plan_products = []

    for i, product_struct in enumerate(structure):
        if i >= len(mappings.product_mapping.hierarchy):
            continue

        product_map = mappings.product_mapping.hierarchy[i]

        plan_components = []
        for j, comp_struct in enumerate(product_struct.components):
            if j >= len(product_map.components):
                continue

            comp_map = product_map.components[j]

            plan_features = []
            for k, feat in enumerate(comp_struct.features):
                if k >= len(comp_map.features):
                    continue
                feat_map = comp_map.features[k]
                plan_features.append({
                    "id": feat["id"],
                    "currentName": feat["name"],
                    "newName": feat_map.new_name,
                })

            plan_components.append({
                "id": comp_struct.id,
                "currentName": comp_struct.name,
                "newName": comp_map.new_name,
                "features": plan_features,
            })

        plan_products.append({
            "id": product_struct.id,
            "currentName": product_struct.name,
            "newName": product_map.new_name,
            "components": plan_components,
        })

    return RenamePlan(products=plan_products)

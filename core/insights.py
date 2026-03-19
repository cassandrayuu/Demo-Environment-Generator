"""
User insights/notes generation.

Generates and pushes realistic user feedback notes to Productboard.
Uses LLM generation when available, with template fallback.
"""

import json
import os
import random
import re
import uuid
from dataclasses import dataclass
from typing import Dict, Generator, List, Optional

from .models import StepResult, StepStatus
from .pb_client import ProductboardClient, ProductboardError, default_client


# Note templates with placeholders for features and company
NOTE_TEMPLATES = [
    {
        "sentiment": "positive",
        "tone": "formal",
        "source": "Support",
        "title_template": "Feature feedback from {company} - Excellent experience with {feature1}",
        "content_template": """Dear Support Team,

I wanted to reach out to express my sincere appreciation for the recent improvements to {feature1}. Our team at {company} has been using this functionality extensively over the past quarter, and the enhancements have significantly streamlined our daily workflows. The integration with {feature2} has been particularly seamless, allowing us to reduce our processing time by approximately 30%.

Furthermore, I would like to highlight how {feature3} has transformed our approach to data management. Previously, we struggled with maintaining consistency across departments, but the new capabilities have addressed these challenges comprehensively. Our finance team especially appreciates the automated reconciliation features that come with {feature2}.

In conclusion, we are extremely satisfied with the direction the product is taking. The combination of {feature1} and {feature3} provides exactly the kind of robust solution we were looking for. We look forward to seeing continued development in these areas and would be happy to participate in any beta programs for upcoming features.

Best regards,
{user_name}
{company}""",
    },
    {
        "sentiment": "negative",
        "tone": "formal",
        "source": "Sales POC",
        "title_template": "Concerns regarding {feature1} implementation at {company}",
        "content_template": """To Whom It May Concern,

I am writing to formally document several concerns that have arisen during our proof-of-concept evaluation at {company}. While we initially had high expectations for {feature1}, the current implementation has not met our requirements in several critical areas. Specifically, the performance degradation when processing large datasets has been unacceptable for our production environment.

Additionally, the integration between {feature2} and {feature3} appears to have significant gaps that were not apparent during the initial demonstration. Our technical team has spent considerable time attempting to work around these limitations, but the workarounds introduce additional complexity that we cannot sustain long-term. The lack of bulk operations in {feature2} is particularly problematic for our scale.

We remain interested in the product and believe it has potential, however, these issues must be addressed before we can proceed with a full deployment. We would appreciate a technical discussion to understand the roadmap for {feature1} improvements and whether the {feature3} integration challenges are being prioritized. Please arrange a call at your earliest convenience.

Sincerely,
{user_name}
Director of Operations
{company}""",
    },
    {
        "sentiment": "neutral",
        "tone": "informal",
        "source": "Customer interview",
        "title_template": "Zoom call notes - {company} feedback on {feature1}",
        "content_template": """Transcript excerpt from customer interview with {user_name} at {company}:

So yeah, we've been using {feature1} for about six months now. It's... fine, I guess? Like, it does what it's supposed to do most of the time. The team has mixed feelings about it honestly. Some folks really like how it integrates with {feature2}, especially the sales team - they say it saves them maybe an hour a day on reporting. But then the ops people are kinda frustrated because {feature3} doesn't quite work the way they expected.

I think the main thing is we're still figuring out the best way to use it for our specific workflow at {company}. Like, the documentation says you can do X with {feature2}, but when we actually tried it, there were a bunch of edge cases that weren't covered. Not a dealbreaker, just... you know, takes more time than we thought to get everything set up right.

Oh, and one more thing - we'd love to see better mobile support for {feature1}. Half our team is remote now and they're always on their phones checking stuff. The current mobile experience for {feature3} is pretty clunky. Anyway, overall it's been okay. Not amazing, not terrible. We're cautiously optimistic about where things are heading.""",
    },
    {
        "sentiment": "positive",
        "tone": "informal",
        "source": "Sales POC",
        "title_template": "Slack thread - {company} team loving {feature1}!",
        "content_template": """#general channel - {company} workspace

{user_name}: hey everyone just wanted to give a shoutout to the new {feature1} update!!

{user_name}: seriously this is a game changer for how we handle our weekly reporting. used to take me like 2 hours every friday and now it's basically automated

teammate1: omg yes! and have you tried using it with {feature2}? the combo is *chef's kiss*

{user_name}: YES! that's exactly what i was going to say next. the way {feature2} pulls data directly into {feature1} is so smooth now. no more copy-pasting between spreadsheets

teammate2: wait you can do that?? i've been doing it manually this whole time

{user_name}: lol yeah check out the {feature3} settings, there's a new sync option. honestly whoever designed that deserves a raise

teammate1: the {feature3} integration is lowkey the best part. we've cut our reconciliation time in half at least

{user_name}: facts. okay back to work but yeah highly recommend everyone check out the new {feature1} stuff if you haven't already. {company} productivity stonks""",
    },
    {
        "sentiment": "negative",
        "tone": "informal",
        "source": "Support",
        "title_template": "Urgent: {feature1} issues affecting {company} operations",
        "content_template": """hey so we're having some major problems over here at {company} and really need some help asap

basically {feature1} has been acting super buggy for the past week. like it'll load fine but then when you try to do anything with {feature2} it just spins forever and eventually times out. we've tried clearing cache, different browsers, even different computers - same issue every time.

this is really messing with our workflow because we rely on {feature1} for all our client reporting. we've had to go back to doing things manually which is taking forever and honestly some of our team is getting pretty frustrated. we promised our clients we'd have reports by end of week and now that's looking really tough.

also noticed that {feature3} seems slower than usual too? not sure if it's related but figured i'd mention it. the whole integration between {feature2} and {feature3} feels like it's struggling under the load.

can someone please look into this? we're a paying customer and this is really affecting our business. happy to get on a call or screenshare or whatever would be helpful. just need this fixed soon.

thanks
{user_name}
{company}""",
    },
]

FIRST_NAMES = [
    "Sarah",
    "Michael",
    "Jennifer",
    "David",
    "Emily",
    "James",
    "Amanda",
    "Robert",
    "Jessica",
    "William",
]
LAST_NAMES = [
    "Johnson",
    "Chen",
    "Martinez",
    "Thompson",
    "Garcia",
    "Anderson",
    "Williams",
    "Brown",
    "Davis",
    "Miller",
]

# Sample customer companies by target company
SAMPLE_COMPANIES_BY_TARGET: Dict[str, List[str]] = {
    "ottimate": [
        "Golder Hospitality",
        "SHG Companies",
        "Clutch Coffee Bar",
        "Riverside Bistro Group",
        "Summit Hotel Partners",
    ],
    "doordash": [
        "Chipotle Mexican Grill",
        "The Cheesecake Factory",
        "Wingstop",
        "Papa John's",
        "Panera Bread",
    ],
    "exterro": [
        "Morrison & Foerster LLP",
        "Deloitte Legal",
        "KPMG Law",
        "Baker McKenzie",
        "Latham & Watkins",
    ],
    "salesforce": [
        "Coca-Cola Company",
        "T-Mobile",
        "Unilever",
        "Toyota Financial Services",
        "American Express",
    ],
    "productboard": [
        "Zendesk",
        "UiPath",
        "Avast",
        "Microsoft (Xbox)",
        "Booking.com",
    ],
}

DEFAULT_SAMPLE_COMPANIES = [
    "Acme Corporation",
    "Global Industries Inc",
    "Pinnacle Solutions",
    "Summit Enterprises",
    "Vertex Partners",
]


@dataclass
class GeneratedNote:
    """A generated note ready to be created."""

    title: str
    content: str
    user_email: str
    source: str
    company_name: str
    sentiment: str
    tone: str
    features_referenced: List[str]


# ---------------------------------------------------------------------------
# LLM-based insights generation
# ---------------------------------------------------------------------------

def _extract_domain(website: str) -> str:
    """Extract domain from website URL."""
    website = website.strip()
    if not website.startswith(("http://", "https://")):
        website = f"https://{website}"
    domain = re.sub(r"^https?://", "", website)
    domain = domain.split("/")[0]
    domain = re.sub(r"^www\.", "", domain)
    return domain


def _build_insights_prompt(company: str, website: str, features: List[str], context_text: str = "") -> str:
    """Build prompt for LLM to generate realistic user insights."""
    features_str = ", ".join(features[:15])  # limit to avoid prompt bloat

    # Include context section if available
    context_section = ""
    if context_text:
        context_section = f"""
## About this product (from website)
{context_text}

Use this to understand what the product ACTUALLY does and generate feedback that matches real use cases.
"""

    return f"""Generate realistic, detailed customer feedback notes for a {company} demo.

Company: {company}
Website: {website}
Product features: {features_str}
{context_section}
## Task
Generate 5 high-quality customer feedback notes.

## Requirements

### 1. Customer identity
Each note must come from a REALISTIC COMPANY NAME (not a person):
- For Instagram → brands, agencies, creators (e.g., "Gymshark", "Sephora", "SociallyIn")
- For DoorDash → restaurants, chains, merchants
- For B2B → actual company-style names

DO NOT use placeholders like "User123" or "Test Company".

---

### 2. Content depth (VERY IMPORTANT)
Each note must be:
- 2–4 paragraphs long
- conversational but detailed
- include:
  - context (how they use the product)
  - specific issue or feedback
  - impact on their workflow or business
  - any attempted workarounds or frustrations
  - optional urgency or request

Think:
- support ticket
- escalation email
- customer complaint
- POC feedback

---

### 3. Tone by company type
- Consumer apps → natural, slightly emotional
- B2B → structured but conversational
- Avoid overly formal "Dear Support Team" language unless appropriate

---

### 4. Feature grounding
- Reference the provided features naturally
- Tie feedback to real usage (not generic statements)

---

### 5. Variety
Mix:
- negative (frustration, bugs)
- neutral (observations)
- positive (value, wins)

---

## Output format (JSON array)

[
  {{
    "company": "Gymshark",
    "text": "Full multi-paragraph feedback...",
    "sentiment": "negative",
    "feature": "Reels Algorithm"
  }}
]

Return ONLY valid JSON."""


def _parse_insights_response(response_text: str) -> List[Dict]:
    """Parse LLM response to extract insights JSON."""
    # Try to extract JSON from code blocks first
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response_text)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_str = response_text.strip()

    data = json.loads(json_str)
    if not isinstance(data, list):
        raise ValueError("Expected JSON array")
    return data


# Known company domains for proper email generation
KNOWN_COMPANY_DOMAINS = {
    # Financial
    "wells fargo": "wellsfargo.com",
    "wells fargo bank": "wellsfargo.com",
    "jpmorgan": "jpmorgan.com",
    "jpmorgan chase": "jpmorganchase.com",
    "bank of america": "bankofamerica.com",
    "goldman sachs": "goldmansachs.com",
    "morgan stanley": "morganstanley.com",
    "american express": "americanexpress.com",
    "capital one": "capitalone.com",
    "citibank": "citi.com",
    "citi": "citi.com",
    # Law firms
    "morrison & foerster": "mofo.com",
    "morrison & foerster llp": "mofo.com",
    "baker mckenzie": "bakermckenzie.com",
    "latham & watkins": "lw.com",
    "king & spalding": "kslaw.com",
    "kroll": "kroll.com",
    "kroll associates": "kroll.com",
    "deloitte": "deloitte.com",
    "deloitte legal": "deloitte.com",
    "kpmg": "kpmg.com",
    "kpmg law": "kpmg.com",
    # Tech
    "booking.com": "booking.com",
    "zendesk": "zendesk.com",
    "uipath": "uipath.com",
    "microsoft": "microsoft.com",
    "salesforce": "salesforce.com",
    "merck": "merck.com",
    "merck & co": "merck.com",
    "merck & co.": "merck.com",
    # Food/Restaurant
    "chipotle": "chipotle.com",
    "chipotle mexican grill": "chipotle.com",
    "panera": "panerabread.com",
    "panera bread": "panerabread.com",
    "papa john's": "papajohns.com",
    "papa johns": "papajohns.com",
    "wingstop": "wingstop.com",
    "the cheesecake factory": "thecheesecakefactory.com",
    "cheesecake factory": "thecheesecakefactory.com",
    # Hospitality
    "marriott": "marriott.com",
    "hilton": "hilton.com",
    "hyatt": "hyatt.com",
    # Retail/Brands
    "gymshark": "gymshark.com",
    "sephora": "sephora.com",
    "nike": "nike.com",
    "adidas": "adidas.com",
    "toyota": "toyota.com",
    "coca-cola": "coca-cola.com",
    "coca cola": "coca-cola.com",
    "unilever": "unilever.com",
    "t-mobile": "t-mobile.com",
}


def _get_email_domain(company_name: str) -> str:
    """Get proper email domain for a company name."""
    normalized = company_name.lower().strip()

    # Check known domains first
    if normalized in KNOWN_COMPANY_DOMAINS:
        return KNOWN_COMPANY_DOMAINS[normalized]

    # For unknown companies, create a clean domain
    # Remove common suffixes like Inc, LLC, LLP, Corp, etc.
    clean = re.sub(r'\s+(inc\.?|llc\.?|llp\.?|corp\.?|ltd\.?|company|co\.?)$', '', normalized, flags=re.IGNORECASE)
    # Convert to domain format: "Wells Fargo Bank" -> "wellsfargobank"
    domain = re.sub(r'[^a-z0-9]', '', clean.lower())
    return f"{domain}.com"


def _insight_to_note(insight: Dict, target_company: str) -> GeneratedNote:
    """Convert parsed insight dict to GeneratedNote."""
    # Use company name from insight (the customer), fall back to generic
    customer_company = insight.get("company", "Customer")

    # Get proper email domain (uses known domains or generates clean one)
    email_domain = _get_email_domain(customer_company)
    email = f"feedback@{email_domain}"

    feature = insight.get("feature")
    features_ref = [feature] if feature else []

    return GeneratedNote(
        title=f"Feedback from {customer_company}: {insight.get('text', '')[:50]}...",
        content=insight.get("text", ""),
        user_email=email,
        source="Support",
        company_name=customer_company,
        sentiment=insight.get("sentiment", "neutral"),
        tone="informal",
        features_referenced=features_ref,
    )


def _generate_llm_notes(company: str, website: str, features: List[str]) -> List[GeneratedNote]:
    """Generate notes using LLM. Raises on failure."""
    # Import LLM callers and context fetcher from generator to avoid duplication
    from .generator import _call_gemini, _call_anthropic, DEFAULT_GEMINI_MODEL, fetch_website_context

    # Fetch website context for grounding (fails gracefully)
    context = fetch_website_context(website)
    context_text = context.to_prompt_section() if context else ""

    prompt = _build_insights_prompt(company, website, features, context_text)

    provider = os.environ.get("LLM_PROVIDER", "gemini").lower()
    print(f"[Insights] Using LLM provider: {provider}", flush=True)

    if provider == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set")
        gemini_model = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
        response_text = _call_gemini(prompt, api_key, gemini_model)
    else:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        response_text = _call_anthropic(prompt, api_key)

    print(f"[Insights] LLM response received, length: {len(response_text)}", flush=True)

    insights = _parse_insights_response(response_text)
    print(f"[Insights] Parsed {len(insights)} insights from LLM", flush=True)

    return [_insight_to_note(ins, company) for ins in insights]


def _get_sample_companies(company: str) -> List[str]:
    """Get relevant sample customer companies for a target company."""
    normalized = company.lower().replace(" ", "").replace("-", "")
    return SAMPLE_COMPANIES_BY_TARGET.get(normalized, DEFAULT_SAMPLE_COMPANIES)


def _generate_user_name() -> tuple:
    """Generate a random user name and email-friendly version."""
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    return f"{first} {last}", f"{first.lower()}.{last.lower()}"


def _generate_note(
    template: dict, features: List[str], note_company: str
) -> GeneratedNote:
    """Generate a single note from a template."""
    # Select 2-4 random features
    num_features = min(random.randint(2, 4), len(features))
    selected_features = random.sample(features, num_features)

    # Pad if we don't have enough features
    while len(selected_features) < 3:
        selected_features.append(selected_features[0])

    user_name, email_name = _generate_user_name()
    email_domain = _get_email_domain(note_company)
    email = f"{email_name}@{email_domain}"

    title = template["title_template"].format(
        company=note_company,
        feature1=selected_features[0],
        feature2=selected_features[1] if len(selected_features) > 1 else selected_features[0],
        feature3=selected_features[2] if len(selected_features) > 2 else selected_features[0],
    )

    content = template["content_template"].format(
        company=note_company,
        user_name=user_name,
        feature1=selected_features[0],
        feature2=selected_features[1] if len(selected_features) > 1 else selected_features[0],
        feature3=selected_features[2] if len(selected_features) > 2 else selected_features[0],
    )

    return GeneratedNote(
        title=title,
        content=content,
        user_email=email,
        source=template["source"],
        company_name=note_company,
        sentiment=template["sentiment"],
        tone=template["tone"],
        features_referenced=selected_features[:num_features],
    )


def generate_notes(
    company: str,
    features: List[str],
    count: int = 5,
) -> List[GeneratedNote]:
    """
    Generate user feedback notes.

    Args:
        company: Target company name (for context and tagging)
        features: List of feature names to reference
        count: Number of notes to generate (default 5)

    Returns:
        List of GeneratedNote objects
    """
    if not features:
        raise ValueError("Features list cannot be empty")

    notes = []
    templates_copy = NOTE_TEMPLATES.copy()
    random.shuffle(templates_copy)

    # Get relevant customer companies
    sample_companies = _get_sample_companies(company)

    for i in range(min(count, len(templates_copy))):
        template = templates_copy[i]
        note_company = sample_companies[i % len(sample_companies)]
        note = _generate_note(template, features, note_company)
        notes.append(note)

    return notes


def generate_insights(
    token: str,
    company: str,
    features: List[str],
    apply: bool = False,
    client: Optional[ProductboardClient] = None,
    website: Optional[str] = None,
) -> StepResult:
    """
    Generate and optionally create user insight notes.

    Args:
        token: Productboard API token
        company: Company name for tagging
        features: List of feature names to reference
        apply: If True, actually create notes; if False, dry-run
        client: Optional ProductboardClient instance
        website: Company website (enables LLM generation when provided)

    Returns:
        StepResult with summary and logs
    """
    client = client or default_client
    logs: List[str] = []
    stats = {"generated": 0, "created": 0, "tagged": 0, "errors": 0}
    used_llm = False

    print(f"[Insights] Starting insights generation for {company}, features count: {len(features)}, apply={apply}", flush=True)

    try:
        # Try LLM generation first if website is provided
        if website:
            try:
                logs.append("Attempting LLM-powered insights generation...")
                notes = _generate_llm_notes(company, website, features)
                used_llm = True
                logs.append(f"Generated {len(notes)} LLM-powered insights")
            except Exception as e:
                print(f"[Insights] LLM generation failed, falling back to templates: {e}", flush=True)
                logs.append(f"LLM generation failed ({type(e).__name__}), using template fallback")
                notes = generate_notes(company, features, count=5)
        else:
            logs.append("Generating template-based user insight notes...")
            notes = generate_notes(company, features, count=5)
        stats["generated"] = len(notes)

        mode_str = "APPLY" if apply else "DRY-RUN"
        logs.append(f"Processing notes ({mode_str} mode)...")

        for i, note in enumerate(notes, 1):
            logs.append(
                f"[Note {i}] {note.title[:50]}... (sentiment: {note.sentiment}, source: {note.source})"
            )

            if apply:
                try:
                    # Create the note
                    note_id = client.create_note(
                        token=token,
                        title=note.title,
                        content=note.content,
                        customer_email=note.user_email,
                        source_origin=note.source,
                        source_record_id=str(uuid.uuid4()),
                        company_name=note.company_name,
                    )

                    if note_id:
                        print(f"[Insights] Created note: {note_id}", flush=True)
                        logs.append(f"  Created note: {note_id}")
                        stats["created"] += 1

                        # Tag the note
                        if client.tag_note(token, note_id, company):
                            logs.append(f"  Tagged with '{company}'")
                            stats["tagged"] += 1
                        else:
                            logs.append(f"  Warning: Failed to tag (note was still created)")
                    else:
                        print("[Insights] Error: create_note returned None", flush=True)
                        logs.append(f"  Error: Failed to create note")
                        stats["errors"] += 1

                except ProductboardError as e:
                    print(f"[Insights] ProductboardError: {e}", flush=True)
                    logs.append(f"  Error: {e}")
                    stats["errors"] += 1
            else:
                logs.append(f"  Would create note for company: {note.company_name}")
                logs.append(f"  Would tag with: {company}")
                stats["created"] += 1
                stats["tagged"] += 1

        # Determine status
        status = StepStatus.SUCCESS if stats["errors"] == 0 else StepStatus.ERROR

        return StepResult(
            name="generate_insights",
            status=status,
            summary=stats,
            logs=logs,
            error=f"{stats['errors']} errors occurred" if stats["errors"] > 0 else None,
        )

    except Exception as e:
        return StepResult(
            name="generate_insights",
            status=StepStatus.ERROR,
            summary=stats,
            logs=logs,
            error=str(e),
        )


# ---------------------------------------------------------------------------
# Standalone insights generation with streaming progress
# ---------------------------------------------------------------------------

def _build_insights_prompt_with_count(
    company: str,
    website: str,
    context_text: str,
    count: int
) -> str:
    """Build prompt for LLM to generate N insights without pre-defined features."""
    context_section = ""
    if context_text:
        context_section = f"""
## About this product (from website)
{context_text}

Use this context to understand what the product does and generate realistic feature names
and feedback that matches real use cases.
"""

    return f"""Generate {count} realistic, detailed customer feedback notes for a {company} demo.

Company: {company}
Website: {website}
{context_section}
## Task
Generate {count} high-quality customer feedback notes.

You must infer realistic product features from the company/website context.

## Requirements

### 1. Customer identity
Each note must come from a REALISTIC COMPANY NAME (not a person):
- For consumer apps (Instagram, TikTok, etc.) → brands, agencies, creators (e.g., "Gymshark", "Sephora", "SociallyIn")
- For delivery/food (DoorDash, Uber Eats) → restaurants, chains, merchants
- For B2B software → actual company-style names matching the industry

DO NOT use placeholders like "User123" or "Test Company".

---

### 2. Content depth (VERY IMPORTANT)
Each note must be:
- 2–4 paragraphs long
- conversational but detailed
- include:
  - context (how they use the product)
  - specific issue or feedback
  - impact on their workflow or business
  - any attempted workarounds or frustrations
  - optional urgency or request

Think:
- support ticket
- escalation email
- customer complaint
- POC feedback

---

### 3. Tone by company type
- Consumer apps → natural, slightly emotional
- B2B → structured but conversational
- Avoid overly formal "Dear Support Team" language unless appropriate

---

### 4. Feature grounding
- Reference realistic product features naturally
- Tie feedback to real usage (not generic statements)

---

### 5. Variety
Mix:
- negative (frustration, bugs)
- neutral (observations)
- positive (value, wins)

---

## Output format (JSON array)

[
  {{
    "company": "Gymshark",
    "text": "Full multi-paragraph feedback...",
    "sentiment": "negative",
    "feature": "Reels Algorithm"
  }}
]

Return ONLY valid JSON with exactly {count} items."""


def generate_insights_standalone(
    token: str,
    company: str,
    website: str,
    count: int = 10,
) -> Generator[Dict, None, None]:
    """
    Generate customer feedback notes as a standalone operation with streaming progress.

    Unlike generate_insights(), this function:
    - Does NOT require a pre-defined features list
    - Generates features from company/website context via LLM
    - Yields progress events for each note created
    - Always applies (creates notes in Productboard)

    Args:
        token: Productboard API token
        company: Company name for tagging and context
        website: Company website URL for context
        count: Number of notes to generate (default 10)

    Yields:
        Dict events:
        - {"type": "progress", "current": 1, "total": 10, "note": "...", "company": "..."}
        - {"type": "complete", "created": 10, "failed": 0}
        - {"type": "error", "message": "..."}
    """
    from .generator import _call_gemini, _call_anthropic, DEFAULT_GEMINI_MODEL, fetch_website_context

    client = default_client
    created = 0
    failed = 0

    print(f"[Insights Standalone] Starting generation for {company}, count={count}", flush=True)

    try:
        # Fetch website context for grounding
        print(f"[Insights Standalone] Fetching website context from {website}", flush=True)
        context = fetch_website_context(website)
        context_text = context.to_prompt_section() if context else ""

        # Build prompt for N notes
        prompt = _build_insights_prompt_with_count(company, website, context_text, count)

        # Call LLM
        provider = os.environ.get("LLM_PROVIDER", "gemini").lower()
        print(f"[Insights Standalone] Using LLM provider: {provider}", flush=True)

        if provider == "gemini":
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                yield {"type": "error", "message": "GEMINI_API_KEY not set"}
                return
            gemini_model = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
            response_text = _call_gemini(prompt, api_key, gemini_model)
        else:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                yield {"type": "error", "message": "ANTHROPIC_API_KEY not set"}
                return
            response_text = _call_anthropic(prompt, api_key)

        print(f"[Insights Standalone] LLM response received, length: {len(response_text)}", flush=True)

        # Parse response
        try:
            insights = _parse_insights_response(response_text)
        except Exception as e:
            yield {"type": "error", "message": f"Failed to parse LLM response: {e}"}
            return

        print(f"[Insights Standalone] Parsed {len(insights)} insights", flush=True)

        # Create each note and yield progress
        total = len(insights)
        for i, insight in enumerate(insights, 1):
            note = _insight_to_note(insight, company)

            try:
                note_id = client.create_note(
                    token=token,
                    title=note.title,
                    content=note.content,
                    customer_email=note.user_email,
                    source_origin=note.source,
                    source_record_id=str(uuid.uuid4()),
                    company_name=note.company_name,
                )

                if note_id:
                    print(f"[Insights Standalone] Created note {i}/{total}: {note_id}", flush=True)
                    created += 1

                    # Tag with company name
                    client.tag_note(token, note_id, company)

                    yield {
                        "type": "progress",
                        "current": i,
                        "total": total,
                        "note": note.title[:60],
                        "company": note.company_name,
                    }
                else:
                    print(f"[Insights Standalone] Failed to create note {i}/{total}", flush=True)
                    failed += 1
                    yield {
                        "type": "progress",
                        "current": i,
                        "total": total,
                        "note": f"Failed: {note.title[:40]}",
                        "company": note.company_name,
                    }

            except ProductboardError as e:
                print(f"[Insights Standalone] Error creating note {i}/{total}: {e}", flush=True)
                failed += 1
                yield {
                    "type": "progress",
                    "current": i,
                    "total": total,
                    "note": f"Error: {str(e)[:40]}",
                    "company": note.company_name,
                }

        # Done
        yield {
            "type": "complete",
            "created": created,
            "failed": failed,
        }

    except Exception as e:
        print(f"[Insights Standalone] Error: {e}", flush=True)
        yield {"type": "error", "message": str(e)}

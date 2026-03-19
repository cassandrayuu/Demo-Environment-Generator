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
from typing import Dict, List, Optional

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


def _build_insights_prompt(company: str, website: str, features: List[str]) -> str:
    """Build prompt for LLM to generate realistic user insights."""
    domain = _extract_domain(website)
    features_str = ", ".join(features[:15])  # limit to avoid prompt bloat

    return f"""Generate realistic user feedback for a {company} product demo.

**Company**: {company}
**Website**: {website}
**Domain**: {domain}
**Product Features**: {features_str}

## Task
Generate 7 diverse user feedback entries that feel authentic for {company}'s customer base.

## Guidelines
- Match the company type:
  - Consumer apps (Instagram, TikTok, Snapchat): casual, emotional, short messages
  - Delivery/logistics (DoorDash, Uber, Instacart): mix of merchants, customers, drivers
  - B2B SaaS: natural but more structured
  - Enterprise: professional but not formal letter style
- Reference features naturally (not every insight needs one)
- Mix of positive, negative, and neutral sentiment
- Personas should match the company's actual user base
- Feedback styles: support tickets, slack messages, interview quotes, NPS comments, sales call notes

## Output Format
Return ONLY a JSON array:
```json
[
  {{
    "text": "The feedback text (2-4 sentences max)",
    "persona": "Creator" or "Merchant" or "Driver" or "Admin" etc.,
    "sentiment": "positive" or "negative" or "neutral",
    "feature": "Feature name or null",
    "source": "Support" or "NPS Survey" or "Customer Interview" or "Slack" or "Sales POC"
  }}
]
```

Return ONLY the JSON array, no other text."""


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


def _insight_to_note(insight: Dict, company: str) -> GeneratedNote:
    """Convert parsed insight dict to GeneratedNote."""
    # Generate email for persona
    persona = insight.get("persona", "User")
    email_name = persona.lower().replace(" ", ".") + str(random.randint(100, 999))
    email_domain = re.sub(r"[^a-z0-9]", "", company.lower())
    email = f"{email_name}@{email_domain}-user.com"

    feature = insight.get("feature")
    features_ref = [feature] if feature else []

    return GeneratedNote(
        title=f"Feedback from {persona}: {insight.get('text', '')[:50]}...",
        content=insight.get("text", ""),
        user_email=email,
        source=insight.get("source", "Support"),
        company_name=company,
        sentiment=insight.get("sentiment", "neutral"),
        tone="informal",
        features_referenced=features_ref,
    )


def _generate_llm_notes(company: str, website: str, features: List[str]) -> List[GeneratedNote]:
    """Generate notes using LLM. Raises on failure."""
    # Import LLM callers from generator to avoid duplication
    from .generator import _call_gemini, _call_anthropic, DEFAULT_GEMINI_MODEL

    prompt = _build_insights_prompt(company, website, features)

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
    email_domain = re.sub(r"[^a-z0-9]", "", note_company.lower())
    email = f"{email_name}@{email_domain}.com"

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

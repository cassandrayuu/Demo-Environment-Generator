#!/usr/bin/env python3
"""
Productboard User Insights Generator

Generates and pushes 5 user insight notes to Productboard for a given company.
Each note references real feature names and includes varied sentiment/tone.
"""

import argparse
import os
import random
import re
import sys
import time
import uuid
from typing import Optional

import requests

API_BASE = "https://api.productboard.com"
MAX_RETRIES = 5
INITIAL_BACKOFF = 1.0

# Note templates with placeholders for features and company
# Each template has: sentiment, tone, source, and content structure
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
{company}"""
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
{company}"""
    },
    {
        "sentiment": "neutral",
        "tone": "informal",
        "source": "Customer interview",
        "title_template": "Zoom call notes - {company} feedback on {feature1}",
        "content_template": """Transcript excerpt from customer interview with {user_name} at {company}:

So yeah, we've been using {feature1} for about six months now. It's... fine, I guess? Like, it does what it's supposed to do most of the time. The team has mixed feelings about it honestly. Some folks really like how it integrates with {feature2}, especially the sales team - they say it saves them maybe an hour a day on reporting. But then the ops people are kinda frustrated because {feature3} doesn't quite work the way they expected.

I think the main thing is we're still figuring out the best way to use it for our specific workflow at {company}. Like, the documentation says you can do X with {feature2}, but when we actually tried it, there were a bunch of edge cases that weren't covered. Not a dealbreaker, just... you know, takes more time than we thought to get everything set up right.

Oh, and one more thing - we'd love to see better mobile support for {feature1}. Half our team is remote now and they're always on their phones checking stuff. The current mobile experience for {feature3} is pretty clunky. Anyway, overall it's been okay. Not amazing, not terrible. We're cautiously optimistic about where things are heading."""
    },
    {
        "sentiment": "positive",
        "tone": "informal",
        "source": "Sales POC",
        "title_template": "Slack thread - {company} team loving {feature1}!",
        "content_template": """#general channel - {company} workspace

{user_name}: hey everyone just wanted to give a shoutout to the new {feature1} update!! 🎉

{user_name}: seriously this is a game changer for how we handle our weekly reporting. used to take me like 2 hours every friday and now it's basically automated

teammate1: omg yes! and have you tried using it with {feature2}? the combo is *chef's kiss*

{user_name}: YES! that's exactly what i was going to say next. the way {feature2} pulls data directly into {feature1} is so smooth now. no more copy-pasting between spreadsheets

teammate2: wait you can do that?? i've been doing it manually this whole time 😭

{user_name}: lol yeah check out the {feature3} settings, there's a new sync option. honestly whoever designed that deserves a raise

teammate1: the {feature3} integration is lowkey the best part. we've cut our reconciliation time in half at least

{user_name}: facts. okay back to work but yeah highly recommend everyone check out the new {feature1} stuff if you haven't already. {company} productivity stonks 📈"""
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
{company}"""
    }
]

FIRST_NAMES = ["Sarah", "Michael", "Jennifer", "David", "Emily", "James", "Amanda", "Robert", "Jessica", "William"]
LAST_NAMES = ["Johnson", "Chen", "Martinez", "Thompson", "Garcia", "Anderson", "Williams", "Brown", "Davis", "Miller"]

# Sample customer companies by target company
# Each key is a company name (lowercase), value is list of realistic customers for that company
SAMPLE_COMPANIES_BY_TARGET = {
    "ottimate": [
        "Golder Hospitality",      # Real Ottimate customer - hotel management group
        "SHG Companies",           # Real Ottimate customer - 60+ hotel locations
        "Clutch Coffee Bar",       # Real Ottimate customer - coffee chain
        "Riverside Bistro Group",  # Realistic restaurant group name
        "Summit Hotel Partners"    # Realistic hospitality company name
    ],
    "doordash": [
        "Chipotle Mexican Grill",  # Major DoorDash restaurant partner
        "The Cheesecake Factory",  # Large casual dining chain partner
        "Wingstop",                # Fast casual partner
        "Papa John's",             # Pizza delivery partner
        "Panera Bread"             # Fast casual/bakery partner
    ],
    "exterro": [
        "Morrison & Foerster LLP",  # Large law firm
        "Deloitte Legal",           # Big 4 legal services
        "KPMG Law",                 # Big 4 legal services
        "Baker McKenzie",           # Global law firm
        "Latham & Watkins"          # Major law firm
    ],
    "salesforce": [
        "Coca-Cola Company",        # Major Salesforce enterprise customer
        "T-Mobile",                 # Telecom using Sales & Service Cloud
        "Unilever",                 # CPG giant on Salesforce platform
        "Toyota Financial Services", # Financial services customer
        "American Express"          # Financial services & CRM customer
    ],
    "productboard": [
        "Zendesk",                  # Customer service platform using Productboard
        "UiPath",                   # Automation company, Productboard customer
        "Avast",                    # Cybersecurity company using Productboard
        "Microsoft (Xbox)",         # Gaming division uses Productboard
        "Booking.com"               # Travel platform, Productboard customer
    ]
}

# Default fallback companies for unknown targets
DEFAULT_SAMPLE_COMPANIES = [
    "Acme Corporation",
    "Global Industries Inc",
    "Pinnacle Solutions",
    "Summit Enterprises",
    "Vertex Partners"
]


def get_sample_companies(company: str) -> list[str]:
    """Get relevant sample customer companies for a target company."""
    normalized = company.lower().replace(" ", "").replace("-", "")
    return SAMPLE_COMPANIES_BY_TARGET.get(normalized, DEFAULT_SAMPLE_COMPANIES)


def get_token() -> str:
    """Get API token from environment variable."""
    token = os.environ.get("PB_TOKEN")
    if not token:
        print("Error: PB_TOKEN environment variable is not set", file=sys.stderr)
        sys.exit(1)
    return token


def load_features(filepath: str) -> list[str]:
    """Load feature names from file, one per line."""
    try:
        with open(filepath, "r") as f:
            features = [line.strip() for line in f if line.strip()]
        if not features:
            print(f"Error: No features found in {filepath}", file=sys.stderr)
            sys.exit(1)
        return features
    except FileNotFoundError:
        print(f"Error: Features file not found: {filepath}", file=sys.stderr)
        sys.exit(1)


def generate_user_name() -> tuple[str, str]:
    """Generate a random user name and email-friendly version."""
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    return f"{first} {last}", f"{first.lower()}.{last.lower()}"


def generate_note(template: dict, company: str, features: list[str], note_company: str) -> dict:
    """Generate a single note from a template with random features."""
    # Select 2-4 random features
    num_features = min(random.randint(2, 4), len(features))
    selected_features = random.sample(features, num_features)

    # Pad if we don't have enough features
    while len(selected_features) < 3:
        selected_features.append(selected_features[0])

    user_name, email_name = generate_user_name()
    # Use the note_company for the email domain (remove spaces and special characters)
    email_domain = re.sub(r'[^a-z0-9]', '', note_company.lower())
    email = f"{email_name}@{email_domain}.com"

    title = template["title_template"].format(
        company=note_company,
        feature1=selected_features[0],
        feature2=selected_features[1] if len(selected_features) > 1 else selected_features[0],
        feature3=selected_features[2] if len(selected_features) > 2 else selected_features[0]
    )

    content = template["content_template"].format(
        company=note_company,
        user_name=user_name,
        feature1=selected_features[0],
        feature2=selected_features[1] if len(selected_features) > 1 else selected_features[0],
        feature3=selected_features[2] if len(selected_features) > 2 else selected_features[0]
    )

    return {
        "title": title,
        "content": content,
        "user_email": email,
        "source": template["source"],
        "features_referenced": selected_features[:num_features],
        "sentiment": template["sentiment"],
        "tone": template["tone"],
        "note_company": note_company
    }


def api_request_with_retry(
    method: str,
    url: str,
    token: str,
    json_data: Optional[dict] = None
) -> Optional[requests.Response]:
    """Make API request with exponential backoff retry for 429 and 5xx errors."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Version": "1"
    }

    backoff = INITIAL_BACKOFF
    for attempt in range(MAX_RETRIES):
        try:
            if method == "POST":
                response = requests.post(url, headers=headers, json=json_data, timeout=30)
            else:
                response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 429 or (500 <= response.status_code < 600):
                if attempt < MAX_RETRIES - 1:
                    print(f"  Received {response.status_code}, retrying in {backoff:.1f}s...")
                    time.sleep(backoff)
                    backoff *= 2
                    continue

            return response

        except requests.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                print(f"  Request error: {e}, retrying in {backoff:.1f}s...")
                time.sleep(backoff)
                backoff *= 2
                continue
            print(f"  Request failed after {MAX_RETRIES} attempts: {e}")
            return None

    return None


def create_note(token: str, note: dict, tag_company: str) -> Optional[str]:
    """Create a note via the Productboard API. Returns note ID if successful."""
    url = f"{API_BASE}/notes"

    # Use the note's assigned company for the company field
    note_company = note.get("note_company", tag_company)

    payload = {
        "title": note["title"],
        "content": note["content"],
        "customer_email": note["user_email"],
        "source": {
            "origin": note["source"],
            "record_id": str(uuid.uuid4())
        },
        "company": {
            "name": note_company
        }
    }

    response = api_request_with_retry("POST", url, token, payload)

    if response is None:
        print(f"  Failed to create note: No response received")
        return None

    if response.status_code in (200, 201):
        data = response.json()
        note_id = data.get("data", {}).get("id") or data.get("id")
        return note_id
    else:
        snippet = response.text[:200] if response.text else "No response body"
        print(f"  Failed to create note: HTTP {response.status_code}")
        print(f"  Response: {snippet}")
        return None


def tag_note(token: str, note_id: str, tag_name: str) -> bool:
    """Add a tag to a note. Returns True if successful."""
    # URL-encode the tag name for the path
    encoded_tag = requests.utils.quote(tag_name, safe="")
    url = f"{API_BASE}/notes/{note_id}/tags/{encoded_tag}"

    response = api_request_with_retry("POST", url, token, {})

    if response is None:
        print(f"  Failed to tag note: No response received")
        return False

    if response.status_code in (200, 201, 204):
        return True
    else:
        snippet = response.text[:200] if response.text else "No response body"
        print(f"  Failed to tag note: HTTP {response.status_code}")
        print(f"  Response: {snippet}")
        return False


def run_dry_run(notes: list[dict], company: str):
    """Print what would be created without making API calls."""
    print("\n" + "=" * 60)
    print("DRY RUN - No API calls will be made")
    print("=" * 60)

    for i, note in enumerate(notes, 1):
        print(f"\n--- Note {i} ---")
        print(f"Title: {note['title']}")
        print(f"Company (in note): {note.get('note_company', 'N/A')}")
        print(f"Sentiment: {note['sentiment']} | Tone: {note['tone']} | Source: {note['source']}")
        print(f"User Email: {note['user_email']}")
        print(f"Features Referenced: {', '.join(note['features_referenced'])}")
        print(f"Content Preview:\n{note['content'][:200]}...")
        print(f"\nAPI calls that would be made:")
        print(f"  1. POST {API_BASE}/notes (company: {note.get('note_company', 'N/A')})")
        print(f"  2. POST {API_BASE}/notes/{{noteId}}/tags/{company}")

    print("\n" + "=" * 60)
    print(f"Summary: Would create {len(notes)} notes tagged with '{company}'")
    print("=" * 60)


def run_apply(token: str, notes: list[dict], company: str):
    """Actually create notes via the API."""
    print("\n" + "=" * 60)
    print("APPLY MODE - Creating notes via API")
    print("=" * 60)

    created_notes = []

    for i, note in enumerate(notes, 1):
        print(f"\nCreating note {i}/{len(notes)}: {note['title'][:50]}...")

        note_id = create_note(token, note, company)
        if note_id:
            print(f"  Created note with ID: {note_id}")

            print(f"  Adding tag '{company}'...")
            if tag_note(token, note_id, company):
                print(f"  Tag added successfully")
            else:
                print(f"  Warning: Failed to add tag (note was still created)")

            created_notes.append(note_id)
        else:
            print(f"  Skipping tag (note creation failed)")

    print("\n" + "=" * 60)
    print(f"Summary: Created {len(created_notes)}/{len(notes)} notes")
    if created_notes:
        print(f"Note IDs: {', '.join(created_notes)}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Generate and push Productboard User Insights for a company"
    )
    parser.add_argument(
        "--company",
        required=True,
        help="Company name for the insights (required)"
    )
    parser.add_argument(
        "--features",
        required=True,
        help="Path to text file with feature names (one per line)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Preview notes without creating them (default)"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually create the notes via API"
    )

    args = parser.parse_args()

    # Default to dry-run if neither specified
    if not args.apply:
        args.dry_run = True

    # Load features
    features = load_features(args.features)
    print(f"Loaded {len(features)} features from {args.features}")

    # Generate 5 notes using the templates
    notes = []
    templates_copy = NOTE_TEMPLATES.copy()
    random.shuffle(templates_copy)

    # Get relevant customer companies for the target
    sample_companies = get_sample_companies(args.company)

    for i, template in enumerate(templates_copy[:5]):
        # Assign each note to a different sample company (customers of the target company)
        note_company = sample_companies[i % len(sample_companies)]
        note = generate_note(template, args.company, features, note_company)
        notes.append(note)

    print(f"Generated {len(notes)} notes for company '{args.company}'")

    if args.dry_run:
        run_dry_run(notes, args.company)
    else:
        token = get_token()
        run_apply(token, notes, args.company)


if __name__ == "__main__":
    main()

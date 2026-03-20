# Productboard Demo Environment Generator

AI-powered POC demo setup for Productboard. Enter a company name and website, and the system generates realistic product hierarchies, strategy, and user insights tailored to that company using LLM generation.

## What This Project Does

This is a **sales enablement tool** for Productboard. When preparing a demo for a prospect, sales teams need the Productboard space to contain realistic data that resonates with that specific company. This tool automates that process:

1. **User enters**: Company name, website URL, and Productboard API token
2. **System analyzes**: The actual product hierarchy in the Productboard space
3. **LLM generates**: Realistic product names, features, objectives, and initiatives specific to that company's industry
4. **System applies**: Renames entities in Productboard and creates realistic user feedback notes

## Architecture

```
┌─────────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│   React Frontend    │────▶│  Cloudflare Worker   │────▶│   Python Runner     │
│   (CF Pages)        │     │  (Edge API + Auth)   │     │   (Railway/FastAPI) │
└─────────────────────┘     └──────────────────────┘     └─────────────────────┘
         │                            │                            │
         │                            ▼                            ▼
         │                   ┌──────────────────┐         ┌──────────────────┐
         │                   │  Cloudflare D1   │         │   Gemini API     │
         │                   │  (Job Records)   │         │   (LLM Gen)      │
         │                   └──────────────────┘         └──────────────────┘
         │                                                         │
         └─────────────────────────────────────────────────────────┘
                                       │
                                       ▼
                              ┌──────────────────┐
                              │  Productboard    │
                              │  API             │
                              └──────────────────┘
```

### Component Responsibilities

| Component | Location | Purpose |
| --- | --- | --- |
| **React Frontend** | `apps/web/` (Cloudflare Pages) | User interface for entering company info, selecting products, viewing progress |
| **Cloudflare Worker** | `apps/worker/` | Edge proxy, authentication, job state storage (D1) |
| **Python Runner** | `services/runner/` (Railway) | Core business logic, LLM calls, Productboard API operations |
| **Core Modules** | `core/` | Reusable Python logic for generation, API calls, validation |

## Data Flow: Complete Request Lifecycle

### Step 1: Analyze Space
```
Frontend POST /api/analyze { token, company, website }
    → Worker proxies to Runner
    → Runner calls Productboard API to list products
    → Returns: [{ id, name, componentCount }]
```

### Step 2: User Selects Products
Frontend displays products, user selects 1-2 products to rename.

### Step 3: Run POC Generation

## Project Structure

```
hierarchy_sync_staging/
├── core/                          # Python core modules (reusable logic)
│   ├── generator.py              # LLM-powered mapping generation (Gemini/Anthropic)
│   ├── hierarchy.py              # Product/component/feature operations
│   ├── strategy.py               # Objective/key result/initiative operations
│   ├── insights.py               # User feedback note generation (templates)
│   ├── runner.py                 # Orchestration - coordinates all steps
│   ├── pb_client.py              # Productboard API client wrapper
│   ├── models.py                 # Data models (dataclasses)
│   └── validators.py             # Preflight validation logic
│
├── services/runner/              # FastAPI service (deployed to Railway)
│   ├── main.py                   # FastAPI app initialization
│   ├── routes/
│   │   ├── products.py           # /api/analyze endpoint
│   │   ├── run.py                # /api/run endpoint (SSE streaming)
│   │   ├── mappings.py           # /api/mappings/generate endpoint
│   │   └── health.py             # /health endpoint
│   ├── middleware/auth.py        # Bearer token authentication
│   ├── schemas.py                # Pydantic request/response models
│   └── requirements.txt          # Python dependencies
│
├── apps/
│   ├── worker/                   # Cloudflare Worker (edge proxy)
│   │   ├── src/
│   │   │   ├── index.ts          # Main entry point
│   │   │   ├── routes/           # Route handlers
│   │   │   └── types.ts          # TypeScript types
│   │   ├── migrations/           # D1 database migrations
│   │   ├── wrangler.toml         # Wrangler configuration
│   │   └── package.json
│   │
│   └── web/                      # React frontend (Vite + TypeScript)
│       ├── src/
│       │   ├── App.tsx           # Main app component with state machine
│       │   ├── pages/            # Page components (Input, Products, Progress, Complete)
│       │   ├── components/       # Reusable UI components
│       │   └── api/client.ts     # API client functions
│       ├── vite.config.ts
│       └── package.json
│
├── CLAUDE.md                     # This file - LLM context
├── DEPLOYMENT.md                 # Deployment instructions
└── README.md                     # Project overview
```

## LLM Generation Details

### Provider Configuration
The system supports two LLM providers, configured via environment variables:

| Variable | Default | Description |
| --- | --- | --- |
| `LLM_PROVIDER` | `gemini` | `gemini` or `anthropic` |
| `GEMINI_API_KEY` | — | Google AI Studio API key |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model to use |
| `ANTHROPIC_API_KEY` | — | Anthropic API key (if using anthropic) |

### Generation Prompt
Located in `core/generator.py:_build_flexible_generation_prompt()`. The prompt:
1. Provides company name, website, and domain
2. Describes the actual structure (X products, Y components, Z features each)
3. Requests JSON output matching the exact structure
4. Asks for realistic names specific to the company's industry

### Generated Output Structure
```json
{
  "products": [
    {
      "name": "Revenue Intelligence Platform",
      "components": [
        {
          "name": "Conversation Analytics",
          "features": ["Call Recording", "Sentiment Analysis", "Talk Ratio", "Topic Detection"]
        }
      ]
    }
  ],
  "objectives": [
    {
      "name": "Increase Enterprise Adoption",
      "keyResults": ["Secure 10 Fortune 500 accounts", "Reduce enterprise churn by 20%"]
    }
  ],
  "initiatives": ["Launch Industry Benchmarks", "Build Salesforce Integration", ...],
  "featuresList": ["Call Recording", "AI Summaries", "Deal Intelligence", ...]
}
```
```
Frontend POST /api/run (SSE streaming) { token, company, website, selectedProductIds }
    → Worker proxies to Runner
    → Runner executes pipeline:
        1. Analyze structure (fetch components/features for selected products)
        2. Generate mappings (LLM call with company context)
        3. Validate preflight (check structure matches)
        4. Rename product hierarchy (PATCH Productboard API)
        5. Rename strategy hierarchy (PATCH Productboard API)
        6. Generate insights (POST notes to Productboard)
    → Streams progress events back to frontend
```

### Fallback Behavior
If LLM generation fails (quota, auth error, invalid JSON), the system falls back to template-based generation with generic names like "{Company} Platform", "Core Engine", etc.

## Productboard API Operations

### Entities Modified
| Entity | Operation | API Endpoint |
| --- | --- | --- |
| Products | Rename | `PATCH /products/{id}` |
| Components | Rename | `PATCH /components/{id}` |
| Features | Rename | `PATCH /features/{id}` |
| Objectives | Rename | `PATCH /objectives/{id}` |
| Key Results | Rename | `PATCH /key-results/{id}` |
| Initiatives | Rename | `PATCH /initiatives/{id}` |
| Notes | Create | `POST /notes` |

### Position-Based Mapping
The system uses **position-based mapping** (not name-based). Products/components/features are sorted alphabetically and assigned positions 1, 2, 3, etc. This allows the same mapping structure to work across different Productboard spaces regardless of existing names.

## User Insights Generation

Located in `core/insights.py`. Creates 5 realistic user feedback notes using:
- **5 hardcoded templates** with different tones (positive formal, negative formal, neutral informal, etc.)
- **Random feature selection** from the generated features list
- **Curated customer lists** per target company type (e.g., for DoorDash prospects, references Chipotle, Panera, etc.)

This is **template-based, not LLM-generated**, to ensure consistent quality and avoid additional API costs.

## Environment Variables

### Railway (Python Runner)
| Variable | Required | Description |
| --- | --- | --- |
| `RUNNER_SECRET` | Yes | Shared secret for auth with Worker |
| `LLM_PROVIDER` | No | `gemini` (default) or `anthropic` |
| `GEMINI_API_KEY` | Yes* | Google AI Studio API key |
| `GEMINI_MODEL` | No | Model name (default: `gemini-2.0-flash`) |
| `ANTHROPIC_API_KEY` | No* | Required if LLM_PROVIDER=anthropic |

### Cloudflare Worker
| Variable | Required | Description |
| --- | --- | --- |
| `RUNNER_URL` | Yes | Railway runner URL |
| `RUNNER_SECRET` | Yes | Shared secret for auth |

### Frontend (Cloudflare Pages)
| Variable | Required | Description |
| --- | --- | --- |
| `VITE_API_URL` | Yes | Worker API URL |

## Key Files for Modifications

| Change | File(s) |
| --- | --- |
| LLM prompt/generation logic | `core/generator.py` |
| Add new LLM provider | `core/generator.py` (add `_call_<provider>()`) |
| Productboard API operations | `core/pb_client.py` |
| Insight note templates | `core/insights.py` |
| Job orchestration steps | `core/runner.py` |
| API route handlers | `services/runner/routes/` |
| Frontend UI | `apps/web/src/pages/` |

## Local Development

```bash
# Terminal 1: Start Python runner
source .venv/bin/activate
export GEMINI_API_KEY="your-key"
export LLM_PROVIDER="gemini"
PYTHONPATH=. uvicorn services.runner.main:app --reload --port 8000

# Terminal 2: Start frontend
cd apps/web && npm run dev

# Terminal 3 (optional): Start worker
cd apps/worker && npm run dev
```

## Rate Limits (Gemini Free Tier)

| Model | RPM | RPD | TPM |
| --- | --- | --- | --- |
| gemini-2.5-flash-lite | 30 | 1,500 | 1,000,000 |
| gemini-2.0-flash | 15 | 1,500 | 1,000,000 |
| gemini-1.5-flash | 15 | 1,500 | 1,000,000 |

Each POC generation uses ~2,200 tokens, so free tier supports ~1,500 generations/day.

## Deployment URLs

| Component | URL |
| --- | --- |
| Frontend | https://demo.pb-gtm-apps.com/ |
| Worker API | (internal, proxied by frontend) |
| Runner API | (Railway, accessed by Worker only) |

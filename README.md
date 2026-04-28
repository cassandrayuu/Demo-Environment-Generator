# Productboard Demo Tools

**https://demo.pb-gtm-apps.com/**

An AI-powered demo preparation suite built for Productboard Sales Engineers. These tools eliminate the repetitive, time-consuming work of preparing prospect-specific demos by automating research, content generation, and space customization.

---

## The Problem

Every sales demo benefits from personalization—but manual prep doesn't scale:

- **Generic demos** are fast but feel impersonal. Prospects see "Acme Corp" and mentally disengage.
- **Customized demos** resonate but require hours of research, renaming, and content creation.

This suite automates the customization work, letting you deliver polished, prospect-specific demos without the prep time investment.

---

## The Tools

### 1. Spark Context Generator

**Purpose:** Prepares Productboard's Spark AI to be knowledgeable about a specific prospect

Spark AI is only as useful as the context it has. This tool generates a comprehensive intelligence package that Spark can reference during meetings, enabling it to give contextually relevant responses about the prospect's business, competitive landscape, and stakeholder priorities.

**What It Creates:**
- **Company Intelligence Packet** — Revenue estimates, business model breakdown, technology stack, AI adoption maturity, and known competitive risks
- **Competitive Landscape** — Market dynamics, how competitors segment, and strategic positioning considerations
- **Competitor Deep Dives (3-5)** — Individual profiles with revenue estimates, product strengths/weaknesses, win conditions, and AI positioning
- **Persona Packets (3-6)** — Decision-maker profiles including their KPIs, budget authority, likely objections, and messaging angles that resonate
- **Strategic Intelligence** — Growth phase analysis, resource allocation priorities, and 3-year scenario planning

**Output:** A Google Drive folder containing formatted docs, ready for Spark ingestion

**Time:** ~10 minutes (generation runs in background)

**When to Use:** Enterprise accounts, strategic opportunities, or any demo where Spark AI will be featured prominently

---

### 2. Customer Feedback Notes

**Purpose:** Populates a Productboard space with realistic user feedback

Empty demo spaces feel fake. Real Productboard implementations have hundreds of customer voices flowing in from support tickets, sales calls, and research sessions. This tool generates that "lived-in" feel by creating industry-appropriate feedback notes.

**What It Creates:**
- 5-50 customer feedback notes (configurable)
- Each note includes a realistic company name, user persona, and feature-specific feedback
- Content is tailored to the prospect's industry and typical user vocabulary

**Output:** Notes appear directly in Productboard's Insights inbox

**Time:** 2-3 minutes

**When to Use:** Any demo where you want the Insights module to feel populated, or when demonstrating how Productboard aggregates customer voices

---

### 3. Full Space Customization (Demo Generator)

**Purpose:** Transforms an entire Productboard space to match a prospect's product and business

This is the most comprehensive tool. Rather than demoing a generic "Product A" and "Feature B," you can show the prospect their own product hierarchy with realistic naming throughout.

**What It Does:**
1. Connects to your demo Productboard space via API token
2. Analyzes your existing product structure (products, components, features)
3. Uses AI to generate prospect-appropriate names based on their business
4. Renames all entities across both hierarchies:
   - **Product Hierarchy:** Products → Components → Features
   - **Strategy Hierarchy:** Objectives → Key Results → Initiatives
5. Optionally generates customer feedback notes (integrated with Tool #2)

**Output:** Your demo space now looks like the prospect built it themselves

**Time:** 2-3 minutes

**When to Use:** Bespoke demos where you want the entire space to reflect the prospect's world—their product names, their strategic objectives, their customer terminology

---

## Decision Guide: Which Tool When?

| Scenario | Recommended Tool(s) |
|----------|---------------------|
| Preparing for a Spark AI demo | Spark Context Generator |
| Demo space feels empty, need quick population | Customer Feedback Notes |
| Want the entire space to feel like their product | Full Space Customization |
| High-value enterprise account, full treatment | All three |
| Quick turnaround, minimal prep time | Customer Feedback Notes |
| Strategy-focused demo (OKRs, roadmapping) | Full Space Customization |

---

## The Impact

| Manual Approach | With Demo Tools |
|-----------------|-----------------|
| 2-4 hours of company research | 10 minutes automated |
| Manually renaming 50+ entities | Bulk transformation in 2-3 minutes |
| Generic placeholder content | Industry-specific, realistic voices |
| Inconsistent quality across SEs | Standardized, repeatable output |
| Spark AI lacks context | Spark AI is deeply informed |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                       USER BROWSER                           │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  React Frontend (Cloudflare Pages)                           │
│  ├── LandingPage (tool selector)                             │
│  ├── SparkContextApp (Tool 1)                                │
│  ├── InsightsApp (Tool 2)                                    │
│  └── DemoGeneratorApp (Tool 3)                               │
└──────────────────┬──────────────────────┬────────────────────┘
                   │                      │
     ┌─────────────▼─────────────┐        │ (Tool 1 direct)
     │ Cloudflare Worker         │        │
     │ (Edge API + D1 Database)  │        ▼
     └─────────────┬─────────────┘  ┌─────────────────────────┐
                   │                │ Spark Runner (Node.js)  │
                   ▼                │ ├── Anthropic Claude    │
     ┌─────────────────────────┐   │ └── Google Drive API    │
     │ Python Runner (FastAPI) │   └─────────────────────────┘
     │ ├── Claude/Gemini API   │
     │ └── Productboard API    │
     └─────────────────────────┘
```

---

## Project Structure

```
pb-demo-tools/
├── core/                          # Shared Python business logic
│   ├── pb_client.py              # Productboard API client
│   ├── generator.py              # AI mapping generation
│   ├── hierarchy.py              # Product hierarchy operations
│   ├── strategy.py               # Strategy hierarchy operations
│   ├── insights.py               # Feedback note generation
│   ├── runner.py                 # Job orchestration
│   ├── models.py                 # Data models
│   └── validators.py             # Input validation
│
├── services/
│   ├── runner/                   # Python FastAPI service (Tools 2 & 3)
│   │   ├── main.py              # FastAPI app initialization
│   │   ├── routes/              # API endpoints
│   │   ├── middleware/          # Authentication
│   │   ├── schemas.py           # Request/response models
│   │   ├── Dockerfile           # Railway deployment
│   │   └── requirements.txt
│   │
│   └── spark-runner/            # Node.js Express service (Tool 1)
│       ├── src/
│       │   ├── index.ts         # Express app
│       │   ├── routes/          # API endpoints
│       │   └── lib/             # Anthropic, Google Drive, prompts
│       └── package.json
│
├── apps/
│   ├── worker/                   # Cloudflare Worker (edge proxy)
│   │   ├── src/
│   │   │   ├── index.ts         # Worker entry point
│   │   │   ├── routes/          # Route handlers
│   │   │   └── db/              # D1 database operations
│   │   └── wrangler.toml        # Cloudflare config
│   │
│   └── web/                      # React frontend (Cloudflare Pages)
│       ├── src/
│       │   ├── App.tsx          # Router
│       │   ├── pages/           # Landing page
│       │   └── apps/            # Tool-specific UIs
│       │       ├── spark-context/
│       │       ├── insights/
│       │       └── demo-generator/
│       └── package.json
│
├── CLAUDE.md                     # AI assistant context
├── DEPLOYMENT.md                 # Deployment instructions
└── README.md                     # This file
```

---

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+
- Productboard API token (for testing)

### 1. Start the Python Runner (Tools 2 & 3)

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r services/runner/requirements.txt

# Set environment variables
export GEMINI_API_KEY="your-key"
# or
export ANTHROPIC_API_KEY="your-key"

# Start server
PYTHONPATH=. uvicorn services.runner.main:app --reload --port 8000
```

API available at http://localhost:8000/docs

### 2. Start the Spark Runner (Tool 1)

```bash
cd services/spark-runner
npm install

# Set environment variables
export ANTHROPIC_API_KEY="your-key"
export GOOGLE_SERVICE_ACCOUNT='{"type":"service_account",...}'
export GOOGLE_DRIVE_FOLDER_ID="your-folder-id"

npm run dev
```

API available at http://localhost:8001

### 3. Start the React Frontend

```bash
cd apps/web
npm install
npm run dev
```

UI available at http://localhost:3000

### 4. (Optional) Start the Cloudflare Worker

```bash
cd apps/worker
npm install
npm run dev
```

Worker available at http://localhost:8787

---

## Environment Variables

### Python Runner (Railway)
| Variable | Required | Description |
|----------|----------|-------------|
| `RUNNER_SECRET` | Yes | Shared auth token |
| `ANTHROPIC_API_KEY` | Yes* | Claude API key |
| `GEMINI_API_KEY` | Yes* | Gemini API key |
| `LLM_PROVIDER` | No | `anthropic` or `gemini` (default: gemini) |

*One of Anthropic or Gemini key required

### Spark Runner (Railway)
| Variable | Required | Description |
|----------|----------|-------------|
| `RUNNER_SECRET` | Yes | Shared auth token |
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `GOOGLE_SERVICE_ACCOUNT` | Yes | Google service account JSON |
| `GOOGLE_DRIVE_FOLDER_ID` | Yes | Parent folder for generated docs |

### Cloudflare Worker
| Variable | Required | Description |
|----------|----------|-------------|
| `RUNNER_URL` | Yes | Python runner URL |
| `RUNNER_SECRET` | Yes | Shared auth token |
| `SPARK_RUNNER_URL` | Yes | Spark runner URL |

### React Frontend (Cloudflare Pages)
| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_URL` | Yes | Worker API URL |
| `VITE_SPARK_RUNNER_URL` | Yes | Spark runner URL |

---

## Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed deployment instructions.

### Summary

| Component | Platform | Production URL |
|-----------|----------|----------------|
| React Frontend | Cloudflare Pages | https://demo.pb-gtm-apps.com/ |
| Cloudflare Worker | Cloudflare Workers | (internal) |
| Python Runner | Railway | (internal) |
| Spark Runner | Railway | (internal) |

---

## API Reference

### Python Runner (Port 8000)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/products` | GET | List Productboard space structure |
| `/api/mappings/generate` | POST | Generate AI-powered name mappings |
| `/api/insights` | POST | Create feedback notes (SSE stream) |
| `/api/run` | POST | Execute full transformation (SSE stream) |

### Spark Runner (Port 8001)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/spark-context` | POST | Generate Spark context documents (SSE stream) |

---

## Key Files for Modifications

| Change | File(s) |
|--------|---------|
| Spark document templates | `services/spark-runner/src/lib/prompt.ts` |
| Demo generator LLM prompt | `core/generator.py` |
| Feedback note templates | `core/insights.py` |
| Productboard API operations | `core/pb_client.py` |
| Job orchestration | `core/runner.py` |
| Frontend UI | `apps/web/src/apps/` |

---

## Troubleshooting

| Error | Solution |
|-------|----------|
| "No module named '...'" | Run `source .venv/bin/activate` |
| Invalid token (401) | Check your Productboard API token |
| Insufficient permissions (403) | Ensure token has write access |
| AI generation failed | Check API key environment variables |
| Connection refused | Ensure runner is running on correct port |

---

## License

Internal Productboard tool. Not for external distribution.

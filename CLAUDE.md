# Productboard Demo Tools

AI-powered demo preparation suite for Productboard sales teams. Hosted at **https://demo.pb-gtm-apps.com/**

## Overview

This project provides 3 tools to help sales engineers prepare compelling, company-specific demos:

| Tool | What It Does | Time |
| --- | --- | --- |
| **Spark Context Generator** | Creates strategic research documents for Spark AI meetings | ~10 min |
| **Customer Feedback Notes** | Populates Productboard with realistic user voices | 2-3 min |
| **Full Space Customization** | Transforms entire Productboard space to match prospect's business | 2-3 min |

---

## Tool 1: Spark Context Generator

**Location: services/spark-runner/ (Node.js/Express) + apps/web/src/apps/spark-context/**

Generates strategic intelligence documents for Productboard's Spark AI assistant to use during prospect meetings.

### What It Creates
From just a company name and domain, the LLM generates ~12 detailed documents:
- **Company Intelligence** **Packet - Revenue, business model**, competitive risks, AI maturity
- **Competitive Landscape** **- Market dynamics, competitor segments, strategic** positioning
- **3-5 Competitor Deep Dives - Revenue estimates, win/loss conditions, AI positioning**
- **3-6 Persona Packets - KPIs, budget authority, objections, messaging that resonates**
- **Strategic Intelligence - Growth phases, resource allocation, 3-year scenarios**

### Architecture
```
Frontend → Spark Runner (Railway/Node.js) → Anthropic Claude API → Google Drive
```

### Key Files
| File | Purpose |
| --- | --- |
| `services/spark-runner/src/lib/prompt.ts` | System prompt defining document structures |
| `services/spark-runner/src/lib/anthropic.ts` | LLM call with parallel batch generation |
| `services/spark-runner/src/lib/google-drive.ts` | Google Drive/Docs upload |
| `services/spark-runner/src/routes/spark-context.ts` | SSE streaming endpoint |

### Environment Variables (Spark Runner)
| Variable | Required | Description |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key for Claude |
| `GOOGLE_SERVICE_ACCOUNT` | Yes | JSON credentials for Google Drive |
| `GOOGLE_DRIVE_FOLDER_ID` | Yes | Parent folder for generated docs |
| `RUNNER_SECRET` | Yes | Auth token for API calls |

---

## Tool 2: Customer Feedback Notes (Insights Generator)

**Location: services/runner/ (Python/FastAPI) + apps/web/src/apps/insights/**

Creates realistic customer feedback notes directly in a Productboard space, making demos feel populated with real user voices.

### What It Creates
- 5-50 user feedback notes (configurable)
- Each note has a company name, user persona, and feature-specific feedback
- Notes are LLM-generated to match the prospect's industry

### Architecture
```
Frontend → Cloudflare Worker → Python Runner (Railway) → Gemini/Anthropic → Productboard API
```

### Key Files
| File | Purpose |
| --- | --- |
| `core/insights.py` | Note generation logic with templates |
| `services/runner/routes/insights.py` | SSE streaming endpoint |

---

## Tool 3: Full Space Customization (Demo Generator)

**Location: services/runner/ (Python/FastAPI) + apps/web/src/apps/demo-generator/**

The most comprehensive tool — renames the entire product hierarchy and strategy hierarchy to match a prospect's business, plus generates feedback notes.

### What It Does
1. **Connects** to Productboard space via API token
2. **Analyzes** existing product structure (products, components, features)
3. **Generates** company-specific names using LLM
4. **Renames** products, components, features, objectives, key results, initiatives
5. **Creates** realistic customer feedback notes

### Architecture
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

### Key Files
| File | Purpose |
| --- | --- |
| `core/generator.py` | LLM prompt and response parsing |
| `core/hierarchy.py` | Product/component/feature operations |
| `core/strategy.py` | Objective/key result/initiative operations |
| `core/runner.py` | Job orchestration |
| `core/pb_client.py` | Productboard API wrapper |

### Productboard Entities Modified
| Before | After |
| --- | --- |
| Hours of manual demo prep | Minutes of automated generation |
| Generic product names | Prospect-specific terminology |
| Empty spaces feel fake | Populated with realistic voices |
| No context for Spark AI | Deep strategic intelligence |
| Inconsistent quality | Standardized, repeatable process |

---

## Project Structure

```
hierarchy_sync_staging/
├── core/                          # Python core modules (shared logic)
│   ├── generator.py              # LLM-powered name generation
│   ├── hierarchy.py              # Product hierarchy operations
│   ├── strategy.py               # Strategy hierarchy operations
│   ├── insights.py               # Feedback note generation
│   ├── runner.py                 # Job orchestration
│   ├── pb_client.py              # Productboard API client
│   └── models.py                 # Data models
│
├── services/
│   ├── runner/                   # Python FastAPI service (Railway)
│   │   ├── main.py              # App initialization
│   │   ├── routes/              # API endpoints
│   │   └── middleware/          # Auth
│   │
│   └── spark-runner/            # Node.js Express service (Railway)
│       ├── src/
│       │   ├── index.ts         # App initialization
│       │   ├── routes/          # API endpoints
│       │   └── lib/             # Anthropic, Google Drive, prompts
│       └── package.json
│
├── apps/
│   ├── worker/                   # Cloudflare Worker (edge proxy)
│   │   ├── src/index.ts
│   │   └── wrangler.toml
│   │
│   └── web/                      # React frontend (Cloudflare Pages)
│       ├── src/
│       │   ├── App.tsx          # Router
│       │   └── apps/            # Tool-specific UI
│       │       ├── spark-context/
│       │       ├── insights/
│       │       └── demo-generator/
│       └── package.json
│
├── CLAUDE.md                     # This file
└── DEPLOYMENT.md                 # Deployment instructions
```

---

## Environment Variables

### Python Runner (Railway) - Tools 2 & 3
| Change | File |
| --- | --- |
| Spark document templates | `services/spark-runner/src/lib/prompt.ts` |
| Demo generator LLM prompt | `core/generator.py` |
| Insight note templates | `core/insights.py` |
| Productboard API operations | `core/pb_client.py` |

### Spark Runner (Railway) - Tool 1
| Variable | Required | Description |
| --- | --- | --- |
| `RUNNER_SECRET` | Yes | Shared secret for auth |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key |
| `GOOGLE_SERVICE_ACCOUNT` | Yes | Google service account JSON |
| `GOOGLE_DRIVE_FOLDER_ID` | Yes | Parent folder ID |

### Cloudflare Worker
| Variable | Required | Description |
| --- | --- | --- |
| `RUNNER_URL` | Yes | Python runner URL |
| `RUNNER_SECRET` | Yes | Shared secret |

### Frontend (Cloudflare Pages)
| Variable | Required | Description |
| --- | --- | --- |
| `VITE_API_URL` | Yes | Worker API URL |
| `VITE_SPARK_RUNNER_URL` | Yes | Spark runner URL (bypasses Worker) |

---

## Local Development

```bash
# Terminal 1: Start Python runner (Tools 2 & 3)
source .venv/bin/activate
export GEMINI_API_KEY="your-key"
PYTHONPATH=. uvicorn services.runner.main:app --reload --port 8000

# Terminal 2: Start Spark runner (Tool 1)
cd services/spark-runner
npm run dev  # Runs on port 8001

# Terminal 3: Start frontend
cd apps/web && npm run dev

# Terminal 4 (optional): Start Cloudflare Worker
cd apps/worker && npm run dev
```

---

## Key Files for Modifications

| Change | File(s) |
| --- | --- |
| Spark document templates | `services/spark-runner/src/lib/prompt.ts` |
| Demo generator LLM prompt | `core/generator.py` |
| Productboard API operations | `core/pb_client.py` |
| Insight note templates | `core/insights.py` |
| Job orchestration | `core/runner.py` |
| Frontend UI | `apps/web/src/apps/` |

---

## Deployment URLs

| Component | URL |
| --- | --- |
| Frontend | https://demo.pb-gtm-apps.com/ |
| Worker API | (internal, proxied by frontend) |
| Python Runner | (Railway, accessed by Worker only) |
| Spark Runner | (Railway, accessed directly by frontend) |

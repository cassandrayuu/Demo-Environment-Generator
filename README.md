# Productboard Demo Environment Generator

Generate and apply best-practice demo hierarchies for prospect companies in Productboard. Simply provide a company name and website, and AI generates product hierarchies, strategic hierarchies, and user insights tailored to that company.

## Architecture

```
┌─────────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│   React Frontend    │────▶│  Cloudflare Worker   │────▶│   Python Runner     │
│   (CF Pages)        │     │  (Edge API + Auth)   │     │   (Railway/FastAPI) │
└─────────────────────┘     └──────────────────────┘     └─────────────────────┘
                                      │
                                      ▼
                            ┌──────────────────────┐
                            │    Cloudflare D1     │
                            │    (Job Records)     │
                            └──────────────────────┘
```

## Quick Start (Web App - Local Development)

### 1. Start the Python Runner

```bash
cd "/Users/cassandrayuu/Claude Projects/Workspace/hierarchy_sync_staging"
source .venv/bin/activate
PYTHONPATH=. uvicorn services.runner.main:app --reload --port 8000
```

The runner API will be available at http://localhost:8000/docs

### 2. Start the React Frontend

```bash
cd apps/web
npm install
npm run dev
```

The web UI will be available at http://localhost:3000

### 3. (Optional) Start the Cloudflare Worker

```bash
cd apps/worker
npm install
npm run dev
```

The worker API will be available at http://localhost:8787

---

## Quick Start (CLI - Original Scripts)

### 1. One-Time Setup

```bash
cd "/Users/cassandrayuu/Claude Projects/Workspace/hierarchy_sync_staging"
source .venv/bin/activate
export PB_TOKEN="your-productboard-api-token"
```

### 2. Generate Files for a New Company

In Nimbalyst, ask Claude:
> "Generate POC files for [Company Name] [website.com]"

This creates three files in `prospects/<company>/`:
- `product_mapping.json` - 2 products, 3 components each, 4 features per component
- `strategy_mapping.json` - 3 objectives with 2 key results each, 6 initiatives
- `features.txt` - ~20 feature names for insight generation

### 3. Select Which Products to Rename

```bash
python3 pb_rename_hierarchy.py "prospects/<company>/product_mapping.json" --select
```

### 4. Run the POC Setup

```bash
# Dry run (preview changes)
python3 pb_poc_setup.py --company "<Company Name>" --website "<website.com>" --dry-run

# Apply changes
python3 pb_poc_setup.py --company "<Company Name>" --website "<website.com>" --apply
```

---

## Project Structure

```
hierarchy_sync_staging/
├── core/                          # Python core modules
│   ├── pb_client.py              # Productboard API client
│   ├── generator.py              # AI mapping generation
│   ├── hierarchy.py              # Product hierarchy operations
│   ├── strategy.py               # Strategy operations
│   ├── insights.py               # Note generation
│   ├── runner.py                 # Orchestration
│   └── validators.py             # Validation utilities
│
├── services/
│   └── runner/                   # FastAPI service
│       ├── main.py               # FastAPI app
│       ├── routes/               # API endpoints
│       ├── middleware/           # Auth middleware
│       ├── schemas.py            # Pydantic models
│       ├── Dockerfile            # Railway deployment
│       └── requirements.txt
│
├── apps/
│   ├── worker/                   # Cloudflare Worker
│   │   ├── src/                  # TypeScript source
│   │   ├── migrations/           # D1 migrations
│   │   ├── wrangler.toml         # Wrangler config
│   │   └── package.json
│   │
│   └── web/                      # React frontend
│       ├── src/
│       │   ├── pages/            # Page components
│       │   ├── components/       # UI components
│       │   ├── api/              # API client
│       │   └── App.tsx
│       ├── vite.config.ts
│       └── package.json
│
├── prospects/                    # Company mapping files
│   ├── _templates/              # Template files
│   └── <company>/               # Per-company files
│
├── pb_poc_setup.py              # CLI orchestrator
├── pb_rename_hierarchy.py       # CLI hierarchy rename
├── pb_rename_strategy.py        # CLI strategy rename
└── pb_generate_insights.py      # CLI insights generator
```

---

## API Endpoints

### Runner API (FastAPI - Port 8000)

| Endpoint | Method | Description |
| --- | --- | --- |
| `/health` | GET | Health check |
| `/products/list` | POST | List products in PB space |
| `/mappings/generate` | POST | AI-generate mapping files |
| `/run` | POST | Execute POC setup |
| `/validate` | POST | Preflight validation |

### Worker API (Cloudflare - Port 8787)

| Endpoint | Method | Description |
| --- | --- | --- |
| `/api/products/list` | POST | Proxy to runner |
| `/api/mappings/generate` | POST | Proxy to runner |
| `/api/jobs` | POST | Create and execute job |
| `/api/jobs/:id` | GET | Get job status |
| `/api/jobs` | GET | List recent jobs |

---

## Deployment

### Python Runner (Railway)

1. Create a new Railway project
2. Connect the repository
3. Set root directory to `/`
4. Set build command: `pip install -r services/runner/requirements.txt`
5. Set start command: `uvicorn services.runner.main:app --host 0.0.0.0 --port $PORT`
6. Add environment variables:
  - `RUNNER_SECRET` - Shared secret for auth
  - `ANTHROPIC_API_KEY` - For AI generation

### Cloudflare Worker

```bash
cd apps/worker
npm install

# Create D1 database
wrangler d1 create pb-demo-db

# Update wrangler.toml with database_id

# Run migrations
wrangler d1 migrations apply pb-demo-db --local

# Deploy
wrangler deploy

# Set secrets
wrangler secret put RUNNER_URL
wrangler secret put RUNNER_SECRET
wrangler secret put CF_ACCESS_TEAM_DOMAIN
```

### React Frontend (Cloudflare Pages)

```bash
cd apps/web
npm install
npm run build

# Deploy via Cloudflare Pages dashboard or:
wrangler pages deploy dist
```

---

## Environment Variables

### Runner (Railway)
| Variable | Description |
| --- | --- |
| `RUNNER_SECRET` | Shared secret for worker auth |
| `ANTHROPIC_API_KEY` | Claude API key for AI generation |
| `PORT` | Server port (default: 8000) |

### Worker (Cloudflare)
| Variable | Description |
| --- | --- |
| `RUNNER_URL` | Python runner base URL |
| `RUNNER_SECRET` | Shared secret for runner auth |
| `CF_ACCESS_TEAM_DOMAIN` | Cloudflare Access domain |

### Frontend (Pages)
| Variable | Description |
| --- | --- |
| `VITE_API_URL` | Worker API base URL |

---

## Mapping File Constraints

**CRITICAL**: Files must match these exact structures or scripts will fail.

### product_mapping.json
- **2 products** total
- **3 components** per product
- **4 features** per component

### strategy_mapping.json
- **3 objectives** with **2 key results** each
- **6 initiatives** total

### features.txt
- One feature name per line (10-25 recommended)

---

## Troubleshooting

| Error | Fix |
| --- | --- |
| "No module named 'requests'" | `source .venv/bin/activate` |
| "PB_TOKEN not set" | `export PB_TOKEN="your-token"` |
| "Position out of range" | Use `--select` to choose products |
| API rate limiting | Scripts auto-retry with backoff |
| Invalid token (401) | Check your Productboard API token |
| Insufficient permissions (403) | Ensure token has write access |

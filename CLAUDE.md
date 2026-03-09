# Productboard Demo Environment Generator

AI-powered POC demo setup for Productboard. Enter a company name and website, and the system generates realistic product hierarchies, strategy, and user insights.

## Architecture

```
React Frontend → Cloudflare Worker → FastAPI Runner → Productboard API
     (Pages)        (Edge Proxy)       (Railway)
```

## Project Structure

```
├── core/                    # Python core modules
│   ├── generator.py         # Claude API mapping generation
│   ├── hierarchy.py         # Product hierarchy operations
│   ├── strategy.py          # Strategy operations
│   ├── insights.py          # Note generation (templates)
│   ├── runner.py            # Orchestration
│   ├── pb_client.py         # Productboard API client
│   ├── models.py            # Data models
│   └── validators.py        # Validation utilities
│
├── services/runner/         # FastAPI service (Railway)
│   ├── main.py              # App entry point
│   ├── routes/              # API endpoints
│   ├── schemas.py           # Pydantic models
│   └── requirements.txt
│
├── apps/
│   ├── worker/              # Cloudflare Worker (Edge proxy)
│   └── web/                 # React frontend (Pages)
│
└── DEPLOYMENT.md            # Deployment instructions
```

## Local Development

```bash
# Start Python runner
source .venv/bin/activate
PYTHONPATH=. uvicorn services.runner.main:app --reload --port 8000

# Start frontend (separate terminal)
cd apps/web && npm run dev
```

## Key Files for Modifications

| Change | File(s) |
|--------|---------|
| AI prompt/generation | `core/generator.py` |
| Productboard API calls | `core/pb_client.py` |
| Insight templates | `core/insights.py` |
| Job orchestration | `core/runner.py` |
| API routes | `services/runner/routes/` |

## Environment Variables

| Variable | Where | Purpose |
|----------|-------|---------|
| `ANTHROPIC_API_KEY` | Railway | Claude API for mapping generation |
| `RUNNER_SECRET` | Railway + Worker | Auth between services |
| `RUNNER_URL` | Worker | FastAPI runner endpoint |
| `VITE_API_URL` | Pages | Worker API URL |

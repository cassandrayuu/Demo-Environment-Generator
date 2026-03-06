# Deployment Guide

This guide covers deploying the Productboard Demo Generator to Railway (Python runner) and Cloudflare (Worker + Pages frontend).

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Cloudflare Pages                        │
│                     (React Frontend)                        │
│                     apps/web/dist                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ VITE_API_URL
┌─────────────────────────────────────────────────────────────┐
│                    Cloudflare Worker                        │
│                    (Edge API Proxy)                         │
│                    apps/worker                              │
│                         │                                   │
│                    D1 Database                              │
│                    (Job State)                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ RUNNER_URL + RUNNER_SECRET
┌─────────────────────────────────────────────────────────────┐
│                       Railway                               │
│                    (FastAPI Runner)                         │
│                    services/runner                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ PB_TOKEN (per request)
                        Productboard API
```

---

## Part 1: Railway (Python Runner)

### Prerequisites

- Railway account at [railway.app](https://railway.app)
- Git repository connected to Railway

### Step 1: Create Railway Project

1. Log in to Railway Dashboard
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose this repository

### Step 2: Configure Build Settings

Railway will auto-detect the Dockerfile. If not, manually configure:

| Setting | Value |
|---------|-------|
| Root Directory | `/` (repository root) |
| Builder | Dockerfile |
| Dockerfile Path | `services/runner/Dockerfile` |

### Step 3: Set Environment Variables

In Railway dashboard → **Variables** tab, add:

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `RUNNER_SECRET` | Yes | Shared secret for Worker auth | Generate: `openssl rand -hex 32` |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key for AI generation | `sk-ant-...` |
| `CORS_ORIGINS` | No | Comma-separated allowed origins | `https://your-worker.workers.dev,https://your-app.pages.dev` |

> Railway auto-injects `PORT`. The Dockerfile uses `$PORT` variable.

### Step 4: Deploy

Railway auto-deploys on push. Verify deployment:

```bash
curl https://your-app.up.railway.app/health
```

Expected response:
```json
{"status": "healthy", "version": "1.0.0"}
```

### Step 5: Note Your Railway URL

Copy the Railway URL (e.g., `https://your-app.up.railway.app`). You'll need this for the Cloudflare Worker configuration.

---

## Part 2: Cloudflare Worker

### Prerequisites

- Cloudflare account
- Wrangler CLI installed: `npm install -g wrangler`
- Logged in: `wrangler login`

### Step 1: Create D1 Database

```bash
cd apps/worker

# Create the database
wrangler d1 create pb-demo-db
```

Copy the `database_id` from the output.

### Step 2: Update wrangler.toml

Edit `apps/worker/wrangler.toml`:

```toml
[[d1_databases]]
binding = "DB"
database_name = "pb-demo-db"
database_id = "YOUR_ACTUAL_DATABASE_ID"  # ← Paste here
```

### Step 3: Run Database Migrations

```bash
# Apply migrations to production D1
wrangler d1 migrations apply pb-demo-db
```

### Step 4: Set Worker Secrets

```bash
# Set the Runner URL (from Railway deployment)
wrangler secret put RUNNER_URL
# Paste: https://your-app.up.railway.app

# Set the shared secret (same as Railway's RUNNER_SECRET)
wrangler secret put RUNNER_SECRET
# Paste: your-generated-secret

# (Optional) Cloudflare Access team domain
wrangler secret put CF_ACCESS_TEAM_DOMAIN
# Paste: yourteam.cloudflareaccess.com
```

### Step 5: Deploy Worker

```bash
npm run deploy
```

### Step 6: Note Your Worker URL

After deployment, Wrangler shows the Worker URL (e.g., `https://pb-demo-api.your-subdomain.workers.dev`).

---

## Part 3: Cloudflare Pages (Frontend)

### Option A: Deploy via Wrangler CLI

```bash
cd apps/web

# Install dependencies
npm install

# Build
npm run build

# Deploy to Pages
wrangler pages deploy dist --project-name=pb-demo-web
```

### Option B: Deploy via Dashboard

1. Go to Cloudflare Dashboard → **Pages**
2. Click **"Create application"** → **"Connect to Git"**
3. Select this repository
4. Configure build settings:

| Setting | Value |
|---------|-------|
| Framework preset | Vite |
| Build command | `npm run build` |
| Build output directory | `dist` |
| Root directory | `apps/web` |

### Step: Set Environment Variables

In Pages dashboard → **Settings** → **Environment variables**:

| Variable | Value |
|----------|-------|
| `VITE_API_URL` | `https://pb-demo-api.your-subdomain.workers.dev` |

> **Important**: Environment variables starting with `VITE_` are embedded at build time. After changing, trigger a rebuild.

### Step: Verify Deployment

Visit your Pages URL and test the full flow:
1. Enter company details
2. Select products
3. Run the job

---

## Environment Variables Summary

### Railway (Python Runner)

| Variable | Required | Description |
|----------|----------|-------------|
| `PORT` | Auto | Injected by Railway |
| `RUNNER_SECRET` | Yes | Shared auth secret |
| `ANTHROPIC_API_KEY` | Yes | AI generation |
| `CORS_ORIGINS` | No | Allowed origins (comma-separated) |

### Cloudflare Worker

| Variable | Required | Description |
|----------|----------|-------------|
| `RUNNER_URL` | Yes | Railway service URL |
| `RUNNER_SECRET` | Yes | Shared auth secret |
| `CF_ACCESS_TEAM_DOMAIN` | No | Cloudflare Access domain |

### Cloudflare Pages

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_URL` | Yes | Worker URL (build-time) |

---

## Troubleshooting

### Railway: Container fails to start

Check logs in Railway dashboard. Common issues:
- Missing `ANTHROPIC_API_KEY` - service starts but logs warning
- Missing `RUNNER_SECRET` - service starts with auth disabled

### Worker: "RUNNER_URL not set"

Ensure you ran `wrangler secret put RUNNER_URL` and redeployed.

### Pages: API calls fail

1. Check `VITE_API_URL` is set correctly
2. Verify Worker is deployed and responding
3. Check browser console for CORS errors

### D1: "Table not found"

Run migrations:
```bash
wrangler d1 migrations apply pb-demo-db
```

---

## Security Checklist

- [ ] `RUNNER_SECRET` is a strong random value (32+ bytes)
- [ ] `RUNNER_SECRET` matches between Railway and Worker
- [ ] `CORS_ORIGINS` in Railway restricts to your domains
- [ ] Anthropic API key has appropriate rate limits
- [ ] Consider enabling Cloudflare Access for additional auth

---

## Local Development

### Run Python Runner locally

```bash
cd services/runner
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-key"
uvicorn services.runner.main:app --reload --port 8001
```

### Run Worker locally

```bash
cd apps/worker
wrangler dev --local --persist
```

### Run Frontend locally

```bash
cd apps/web
npm install
npm run dev
```

The frontend proxies `/api` to `localhost:8001` (the Python runner) during development.

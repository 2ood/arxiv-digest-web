# arXiv Digest

A daily arXiv paper digest with semantic + keyword matching, email delivery via SendGrid, and a web UI to manage topics — all running on GitHub Actions + Vercel.

## Architecture

```
GitHub Actions (daily cron)          Vercel (Next.js)
  pipeline/main.py          ←→       /api/topics   (edit topics)
  ├── fetcher.py                      /api/trigger  (manual run)
  ├── filter.py                       app/page.tsx  (UI)
  ├── emailer.py
  └── config_client.py ──────────── Vercel KV (shared config store)
```

## Setup

### 1. Vercel KV

1. Create a Vercel project and add a **KV (Redis)** database from the Vercel dashboard.
2. Copy the KV environment variables (`KV_REST_API_URL`, `KV_REST_API_TOKEN`).

### 2. SendGrid

1. Create a [SendGrid](https://sendgrid.com) account (free tier: 100 emails/day).
2. Create an API key with **Mail Send** permission.
3. Verify your sender email address in SendGrid.

### 3. GitHub Secrets

In your repo → Settings → Secrets → Actions, add:

| Secret | Value |
|---|---|
| `SENDGRID_API_KEY` | Your SendGrid API key |
| `KV_REST_API_URL` | From Vercel KV dashboard |
| `KV_REST_API_TOKEN` | From Vercel KV dashboard |

### 4. Vercel Environment Variables

In Vercel project settings → Environment Variables, add:

| Variable | Value |
|---|---|
| `KV_REST_API_URL` | From Vercel KV dashboard |
| `KV_REST_API_TOKEN` | From Vercel KV dashboard |
| `GITHUB_PAT` | GitHub personal access token (for manual trigger) |
| `GITHUB_OWNER` | Your GitHub username |
| `GITHUB_REPO` | Your repo name |

### 5. Initial config

On first run, the pipeline falls back to built-in defaults (your 3 topics).
Then open the web UI to edit topics — changes are saved to KV and used immediately.

Update `email_to` and `email_from` in the KV config key, or edit `config_client.py` defaults.

### 6. Deploy

```bash
# Deploy web UI
cd web && vercel deploy

# Push to GitHub → Actions will run daily at 08:00 UTC (weekdays)
git push origin main
```

## Local Development

```bash
# Run pipeline locally (without KV — uses config.json fallback)
cd pipeline
pip install -r requirements.txt
python main.py

# Run web UI locally
cd web
npm install
npm run dev
```

## Matching Logic

1. **Keyword layer** — regex match against title + abstract with light stemming (`reasoning` matches `reasoning-based`). Fast, zero dependencies.
2. **Semantic layer** — `all-MiniLM-L6-v2` embeds abstracts and compares cosine similarity against topic descriptions. Only runs on papers that didn't match keywords. Threshold: 0.35 (adjustable in config).

A paper passes if **either** layer fires. Result email groups papers by topic and labels each match method.

## File Structure

```
arxiv-digest/
├── .github/workflows/daily.yml   # Cron: 08:00 UTC Mon-Fri
├── pipeline/
│   ├── main.py                   # Orchestrator
│   ├── fetcher.py                # arXiv API client
│   ├── filter.py                 # Keyword + semantic matching
│   ├── emailer.py                # HTML email via SendGrid
│   ├── config_client.py          # Vercel KV + local fallback
│   └── requirements.txt
├── web/                          # Next.js app → Vercel
│   ├── app/
│   │   ├── page.tsx              # Topic editor UI
│   │   ├── layout.tsx
│   │   └── api/
│   │       ├── topics/route.ts   # GET/POST topics from KV
│   │       └── trigger/route.ts  # Trigger GitHub Actions
│   └── package.json
└── vercel.json
```
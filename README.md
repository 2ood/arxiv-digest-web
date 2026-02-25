# arXiv Digest

A daily personalized arXiv paper digest, published as a static GitHub Pages site.

## How it works

1. GitHub Actions runs every weekday at 08:00 UTC
2. `pipeline/main.py` fetches recent papers from arXiv, filters them by your topics, and writes `index.html`
3. The workflow pushes `index.html` to the `gh-pages` branch
4. GitHub Pages serves it at `https://yourusername.github.io/arxiv-digest`

## Setup

### 1. Fork / clone this repo

### 2. Enable GitHub Pages
- Go to repo **Settings → Pages**
- Set source to **Deploy from branch → gh-pages → / (root)**

### 3. Run it
- Go to **Actions → Daily arXiv Digest → Run workflow** to trigger manually
- Or just wait — it runs automatically at 08:00 UTC on weekdays

That's it. No API keys, no external services.

## Customizing topics

Edit `config.yaml` and push. The next run picks up your changes.

```yaml
topics:
  - name: My Topic
    enabled: true
    terms:
      - keyword one
      - keyword two
    description: "Used for semantic matching — describe what this topic is about"
```

- **`terms`** — keyword/synonym list, matched against title + abstract with light stemming
- **`description`** — plain English description used for semantic (embedding) matching
- **`enabled`** — set to `false` to temporarily disable a topic without deleting it

## Running locally

```bash
pip install -r requirements.txt
python pipeline/main.py
# opens index.html in your browser
```

## File structure

```
arxiv-digest/
├── .github/workflows/daily.yml  # cron + deploy
├── pipeline/
│   ├── main.py                  # orchestrator
│   ├── fetcher.py               # arXiv API client
│   ├── filter.py                # keyword + semantic matching
│   └── renderer.py              # HTML page generator
├── config.yaml                  # your topics
└── requirements.txt
```
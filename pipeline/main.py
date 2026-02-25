"""
main.py — Reads config.yaml, runs the pipeline, writes index.html.
Run locally:  python pipeline/main.py
GitHub Actions runs this and commits index.html to gh-pages.
"""

import sys
import yaml
from pathlib import Path
from datetime import datetime, timezone

# Allow running from repo root or from pipeline/
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from fetcher import fetch_recent_papers
from filter import filter_papers, Topic
from renderer import render_html

CONFIG_PATH = ROOT / "config.yaml"
OUTPUT_PATH = ROOT / "index.html"


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    print("=" * 60)
    print("arXiv Digest")
    print("=" * 60)

    config = load_config()

    topics = [
        Topic(
            id=t["name"].lower().replace(" ", "-"),
            name=t["name"],
            terms=t["terms"],
            description=t["description"],
            enabled=t.get("enabled", True),
        )
        for t in config["topics"]
    ]
    enabled = [t for t in topics if t.enabled]
    print(f"[main] Topics: {[t.name for t in enabled]}")

    papers = fetch_recent_papers(
        categories=config.get("categories", ["cs.AI", "cs.LG", "cs.CL"]),
        max_results=config.get("max_results", 300),
    )

    results = filter_papers(
        papers=papers,
        topics=enabled,
        embedding_threshold=config.get("embedding_threshold", 0.35),
        seen_ids=set(),
    )

    print(f"[main] {len(results)} papers matched.")

    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    html = render_html(results, date_str)

    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"[main] Written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
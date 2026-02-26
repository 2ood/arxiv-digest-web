"""
main.py — Reads config.yaml, runs the pipeline, writes index.html.

Usage:
    python pipeline/main.py           # run pipeline, write index.html
    python pipeline/main.py --preview # same, then open in browser
"""

import sys
import webbrowser
import yaml
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from fetcher import fetch_papers_by_date
from filter import filter_papers, Topic
from renderer import render_html

CONFIG_PATH = ROOT / "config.yaml"
OUTPUT_PATH = ROOT / "index.html"

KST = timezone(timedelta(hours=9))


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    preview = "--preview" in sys.argv

    print("=" * 60)
    print("arXiv Digest" + (" [preview]" if preview else ""))
    print("=" * 60)

    config  = load_config()
    topics  = [
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

    # Fetch papers grouped by date
    papers_by_date = fetch_papers_by_date(
        categories=config.get("categories", ["cs.AI", "cs.LG", "cs.CL"]),
        max_results=config.get("max_results", 2000),
    )

    # Run filter independently for each date
    results_by_date = {}
    for day, papers in papers_by_date.items():
        print(f"\n[main] Filtering {day} ({len(papers)} papers)…")
        matched, unmatched = filter_papers(
            papers=papers,
            topics=enabled,
            embedding_threshold=config.get("embedding_threshold", 0.35),
            seen_ids=set(),
        )
        results_by_date[day] = (matched, unmatched)
        print(f"[main] {day}: {len(matched)} matched, {len(unmatched)} unmatched.")

    date_str = datetime.now(KST).strftime("%B %d, %Y")
    html = render_html(results_by_date, date_str)

    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"\n[main] Written to {OUTPUT_PATH}")

    if preview:
        webbrowser.open(OUTPUT_PATH.as_uri())
        print("[main] Opened in browser.")


if __name__ == "__main__":
    main()
"""
main.py — Reads config.yaml, runs the pipeline, writes index.html + date.html.

Usage:
    python pipeline/main.py           # run pipeline
    python pipeline/main.py --preview # run + open browser
"""

import sys
import json
import webbrowser
import yaml
from pathlib import Path
from datetime import datetime, timezone, timedelta, date

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from fetcher  import fetch_recent_days
from filter   import filter_papers, Topic
from storage  import (
    save_papers,
    load_papers,
    list_available_dates,
    prune_old_files,
    date_has_data,
)
from renderer import render_html

CONFIG_PATH  = ROOT / "config.yaml"
OUTPUT_PATH  = ROOT / "index.html"
DATE_HTML    = ROOT / "date.html"
DATE_TMPL    = Path(__file__).parent.parent / "date.html"
KST          = timezone(timedelta(hours=9))
MAX_TABS     = 7


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_topics(config: dict) -> list[Topic]:
    return [
        Topic(
            id=t["name"].lower().replace(" ", "-"),
            name=t["name"],
            terms=t["terms"],
            description=t["description"],
            enabled=t.get("enabled", True),
        )
        for t in config["topics"]
    ]


def inject_topics_into_date_html(config: dict) -> None:
    """
    Replace the TOPICS_CONFIG placeholder in date.html with the real
    topics from config.yaml so the client-side keyword filter works.
    """
    topics_for_js = [
        {
            "name":    t["name"],
            "enabled": t.get("enabled", True),
            "terms":   t["terms"],
        }
        for t in config["topics"]
    ]
    topics_json = json.dumps(topics_for_js, ensure_ascii=False)

    html = DATE_HTML.read_text(encoding="utf-8")
    html = html.replace(
        "const TOPICS_CONFIG = [];",
        f"const TOPICS_CONFIG = {topics_json};",
    )
    DATE_HTML.write_text(html, encoding="utf-8")
    print(f"[main] Injected {len(topics_for_js)} topics into date.html")


def main():
    preview = "--preview" in sys.argv

    print("=" * 60)
    print("arXiv Digest" + (" [preview]" if preview else ""))
    print("=" * 60)

    config  = load_config()
    topics  = build_topics(config)
    enabled = [t for t in topics if t.enabled]
    print(f"[main] Topics: {[t.name for t in enabled]}")

    # ── 1. Fetch recent days, backfilling missing JSON ───────────────────────
    recent_by_date = fetch_recent_days(
        categories=config.get("categories", ["cs.AI", "cs.LG", "cs.CL"]),
        max_results=config.get("max_results", 2000),
        max_days=MAX_TABS,
    )

    # Save any newly fetched days that don't yet have JSON on disk.
    for d, papers in recent_by_date.items():
        if not date_has_data(ROOT, d):
            save_papers(ROOT, d, papers)
        else:
            print(f"[main] Skipping save for {d} (already exists).")

    # ── 2. Load up to MAX_TABS most recent days from storage ────────────────
    all_dates = list_available_dates(ROOT)
    if not all_dates:
        print("[main] No data available, nothing to render.")
        return

    target_dates = all_dates[:MAX_TABS]
    papers_by_date: dict[date, list] = {}
    for d in target_dates:
        if d in recent_by_date:
            papers_by_date[d] = recent_by_date[d]
        else:
            loaded = load_papers(ROOT, d)
            if loaded is not None:
                papers_by_date[d] = loaded

    print(
        f"\n[main] Data for {len(papers_by_date)} days: "
        f"{sorted(papers_by_date.keys(), reverse=True)}"
    )

    # ── 3. Filter each day ────────────────────────────────────────────────────
    results_by_date: dict[date, tuple] = {}
    for day in sorted(papers_by_date.keys(), reverse=True):
        papers = papers_by_date[day]
        print(f"\n[main] Filtering {day} ({len(papers)} papers)…")
        matched, unmatched = filter_papers(
            papers=papers,
            topics=enabled,
            embedding_threshold=config.get("embedding_threshold", 0.35),
            seen_ids=set(),
        )
        results_by_date[day] = (matched, unmatched)
        print(f"[main] {day}: {len(matched)} matched, {len(unmatched)} unmatched.")

    # ── 4. Render index.html ──────────────────────────────────────────────────
    all_dates = list_available_dates(ROOT)  # all dates with JSON for calendar
    date_str  = datetime.now(KST).strftime("%B %d, %Y")
    html      = render_html(results_by_date, date_str, all_available_dates=all_dates)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"\n[main] Written to {OUTPUT_PATH}")

    # ── 5. Inject topics into date.html ──────────────────────────────────────
    inject_topics_into_date_html(config)

    # ── 6. Prune old JSON files ───────────────────────────────────────────────
    prune_old_files(ROOT, retention_days=config.get("retention_days", 90))

    if preview:
        webbrowser.open(OUTPUT_PATH.as_uri())
        print("[main] Opened in browser.")


if __name__ == "__main__":
    main()
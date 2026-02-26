"""
fetcher.py — Fetches recent papers from arXiv API, up to 7 days back.

Returns papers grouped by submission date (KST), newest date first.
Each group is fetched until we hit a date older than our 7-day window.
"""

import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta, date
from collections import defaultdict


ARXIV_API     = "https://export.arxiv.org/api/query"
CHUNK_SIZE    = 300
REQUEST_DELAY = 3
MAX_DAYS      = 7

NS = {
    "atom": "http://www.w3.org/2005/Atom",
}

KST = timezone(timedelta(hours=9))


@dataclass
class Paper:
    id:         str
    title:      str
    abstract:   str
    authors:    list[str]
    url:        str
    published:  datetime
    categories: list[str]


def _fetch_chunk(category_query: str, start: int) -> list[Paper]:
    params = urllib.parse.urlencode({
        "search_query": category_query,
        "sortBy":       "submittedDate",
        "sortOrder":    "descending",
        "start":        start,
        "max_results":  CHUNK_SIZE,
    })
    with urllib.request.urlopen(f"{ARXIV_API}?{params}", timeout=30) as resp:
        xml_data = resp.read()

    root   = ET.fromstring(xml_data)
    papers = []

    for entry in root.findall("atom:entry", NS):
        raw_id   = entry.find("atom:id", NS).text.strip()
        short_id = raw_id.split("/abs/")[-1].split("v")[0]
        title    = entry.find("atom:title",   NS).text.strip().replace("\n", " ")
        abstract = entry.find("atom:summary", NS).text.strip().replace("\n", " ")
        authors  = [
            a.find("atom:name", NS).text.strip()
            for a in entry.findall("atom:author", NS)
        ]
        published_str = entry.find("atom:published", NS).text.strip()
        published     = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        categories    = [tag.get("term") for tag in entry.findall("atom:category", NS)]

        papers.append(Paper(
            id=short_id, title=title, abstract=abstract,
            authors=authors, url=f"https://arxiv.org/abs/{short_id}",
            published=published, categories=categories,
        ))

    return papers


def fetch_papers_by_date(
    categories: list[str] = ["cs.AI"],
    max_results: int = 2000,
) -> dict[date, list[Paper]]:
    """
    Fetch recent papers grouped by submission date (KST).
    Returns dict: date → [Paper, ...], covering up to MAX_DAYS days.
    Dates are sorted newest-first as dict keys.
    Stops paginating once all papers in a chunk are older than the window.
    """
    today_kst   = datetime.now(KST).date()
    cutoff      = today_kst - timedelta(days=MAX_DAYS - 1)
    cat_query   = " OR ".join(f"cat:{c}" for c in categories)

    grouped:  dict[date, list[Paper]] = defaultdict(list)
    seen_ids: set[str]                = set()
    start = 0

    print(f"[fetcher] Fetching papers {cutoff} → {today_kst} (KST) from {categories}…")

    while start < max_results:
        print(f"[fetcher] Requesting papers {start+1}–{start+CHUNK_SIZE}…")
        papers = _fetch_chunk(cat_query, start)

        if not papers:
            print("[fetcher] Empty response — stopping.")
            break

        all_too_old = True
        for p in papers:
            paper_date = p.published.astimezone(KST).date()
            if paper_date < cutoff:
                continue   # older than window, skip
            all_too_old = False
            if p.id not in seen_ids:
                seen_ids.add(p.id)
                grouped[paper_date].append(p)

        in_window = sum(len(v) for v in grouped.values())
        print(f"[fetcher] {in_window} papers in window so far.")

        # If every paper in this chunk was outside the window, stop
        if all_too_old:
            print("[fetcher] All papers older than window — stopping.")
            break

        if len(papers) < CHUNK_SIZE:
            print("[fetcher] Partial page — end of results.")
            break

        start += CHUNK_SIZE
        print(f"[fetcher] Waiting {REQUEST_DELAY}s…")
        time.sleep(REQUEST_DELAY)

    # Return as sorted dict, newest date first
    sorted_grouped = dict(
        sorted(grouped.items(), reverse=True)
    )
    for d, papers in sorted_grouped.items():
        print(f"[fetcher]   {d}: {len(papers)} papers")

    print(f"[fetcher] Done. {sum(len(v) for v in sorted_grouped.values())} total papers across {len(sorted_grouped)} days.")
    return sorted_grouped
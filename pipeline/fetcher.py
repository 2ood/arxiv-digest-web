"""
fetcher.py — Fetches today's papers from arXiv API.

arXiv API hard limit: 300 results per request.
Paginates in chunks of 300, stopping when we hit papers
submitted before today (KST). Returns a flat list for today only.
Past days are loaded from storage, not fetched live.
"""

import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta, date


ARXIV_API     = "https://export.arxiv.org/api/query"
CHUNK_SIZE    = 300
REQUEST_DELAY = 3

NS = {"atom": "http://www.w3.org/2005/Atom"}

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
        authors  = [a.find("atom:name", NS).text.strip()
                    for a in entry.findall("atom:author", NS)]
        published = datetime.fromisoformat(
            entry.find("atom:published", NS).text.strip().replace("Z", "+00:00"))
        categories = [tag.get("term") for tag in entry.findall("atom:category", NS)]

        papers.append(Paper(
            id=short_id, title=title, abstract=abstract,
            authors=authors, url=f"https://arxiv.org/abs/{short_id}",
            published=published, categories=categories,
        ))
    return papers


def fetch_recent_days(
    categories: list[str] = ["cs.AI"],
    max_results: int = 2000,
    max_days: int = 7,
) -> dict[date, list[Paper]]:
    """
    Fetch up to max_days of the most recent papers from arXiv, grouped by
    their KST calendar date.

    This walks the arXiv feed in reverse-chronological order and associates
    each paper with its KST date. Once we've fully passed beyond the oldest
    date we care about (the max_days‑th distinct date we encounter), we stop.
    """
    if max_days <= 0:
        return {}

    cat_query = " OR ".join(f"cat:{c}" for c in categories)
    per_day: dict[date, list[Paper]] = {}
    dates_in_order: list[date] = []
    seen_ids: set[str] = set()
    target_last_date: date | None = None

    start = 0
    print(
        f"[fetcher] Fetching up to {max_days} recent day(s) of papers "
        f"from {categories}…"
    )

    while start < max_results:
        print(f"[fetcher] Requesting papers {start+1}–{start+CHUNK_SIZE}…")
        chunk = _fetch_chunk(cat_query, start)

        if not chunk:
            print("[fetcher] Empty response — stopping.")
            break

        hit_past = False
        for p in chunk:
            paper_date_kst = p.published.astimezone(KST).date()

            # Once we've identified the oldest date we care about, as soon as we
            # see a paper from an earlier day we can stop — results are sorted
            # newest‑first, so everything after will be even older.
            if target_last_date is not None and paper_date_kst < target_last_date:
                hit_past = True
                break

            if p.id in seen_ids:
                continue
            seen_ids.add(p.id)

            if paper_date_kst not in per_day:
                per_day[paper_date_kst] = []
                dates_in_order.append(paper_date_kst)

                if len(dates_in_order) == max_days:
                    target_last_date = paper_date_kst

            per_day[paper_date_kst].append(p)

        if hit_past:
            print(
                f"[fetcher] Reached earlier than {target_last_date} — "
                "stopping."
            )
            break

        if len(chunk) < CHUNK_SIZE:
            print("[fetcher] Partial page — end of results.")
            break

        start += CHUNK_SIZE
        print(f"[fetcher] Waiting {REQUEST_DELAY}s…")
        time.sleep(REQUEST_DELAY)

    print(
        "[fetcher] Done. Got "
        + ", ".join(
            f"{len(per_day[d])} for {d.isoformat()}" for d in sorted(per_day.keys(), reverse=True)
        )
        or "[fetcher] Done. No papers fetched."
    )
    return per_day


def fetch_today(
    categories: list[str] = ["cs.AI"],
    max_results: int = 2000,
) -> tuple[date, list[Paper]]:
    """
    Fetch the most recent "day" of papers from arXiv, using KST for day
    boundaries but deriving the actual digest date from the newest papers
    returned by the API.

    Concretely:
      - We look at the newest paper's published timestamp (converted to KST)
      - That paper's KST date becomes the "digest day"
      - We keep consuming papers while their KST date == digest day
      - As soon as we hit an older date, we stop (results are sorted newest-first)

    This avoids issues where the local calendar day (in KST) has advanced
    but arXiv's "published" dates have not yet rolled over, which would
    otherwise yield zero papers for "today".

    Returns (digest_date_kst, papers).
    """
    cat_query        = " OR ".join(f"cat:{c}" for c in categories)
    all_papers: list[Paper] = []
    seen_ids:   set[str]    = set()
    digest_date: date | None = None
    start = 0

    print(f"[fetcher] Fetching most recent papers from {categories}…")

    while start < max_results:
        print(f"[fetcher] Requesting papers {start+1}–{start+CHUNK_SIZE}…")
        chunk = _fetch_chunk(cat_query, start)

        if not chunk:
            print("[fetcher] Empty response — stopping.")
            break

        new_today: list[Paper] = []
        hit_old = False
        for p in chunk:
            paper_date_kst = p.published.astimezone(KST).date()

            # Establish digest_date from the first (newest) paper we see.
            if digest_date is None:
                digest_date = paper_date_kst

            if paper_date_kst == digest_date:
                if p.id not in seen_ids:
                    seen_ids.add(p.id)
                    new_today.append(p)
            else:
                # We've crossed into an older day; since results are sorted
                # newest-first, everything after this is older too.
                hit_old = True
                break

        all_papers.extend(new_today)
        print(f"[fetcher] +{len(new_today)} (total today: {len(all_papers)})")

        if hit_old:
            print("[fetcher] Reached yesterday — done.")
            break
        if len(chunk) < CHUNK_SIZE:
            print("[fetcher] Partial page — end of results.")
            break

        start += CHUNK_SIZE
        print(f"[fetcher] Waiting {REQUEST_DELAY}s…")
        time.sleep(REQUEST_DELAY)

    # Fallback: if for some reason we saw no papers at all, use "today" in KST
    # as the digest date so the rest of the pipeline still has a sensible key.
    digest_date_final = digest_date or datetime.now(KST).date()

    print(f"[fetcher] Done. {len(all_papers)} papers for {digest_date_final}.")
    return digest_date_final, all_papers
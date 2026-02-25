"""
fetcher.py — Fetches recent papers from arXiv API for a given category.
"""

import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


ARXIV_API = "https://export.arxiv.org/api/query"
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


@dataclass
class Paper:
    id: str            # e.g. "2401.12345"
    title: str
    abstract: str
    authors: list[str]
    url: str
    published: datetime
    categories: list[str]


def fetch_recent_papers(
    categories: list[str] = ["cs.AI"],
    max_results: int = 300,
) -> list[Paper]:
    """
    Fetch recent submitted papers from arXiv for the given categories.
    Uses the arXiv API search endpoint sorted by submission date.
    """
    category_query = " OR ".join(f"cat:{c}" for c in categories)
    params = urllib.parse.urlencode({
        "search_query": category_query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": max_results,
    })
    url = f"{ARXIV_API}?{params}"

    print(f"[fetcher] Fetching up to {max_results} papers from: {categories}")
    with urllib.request.urlopen(url, timeout=30) as resp:
        xml_data = resp.read()

    root = ET.fromstring(xml_data)
    papers = []

    for entry in root.findall("atom:entry", NS):
        raw_id = entry.find("atom:id", NS).text.strip()
        # Extract short ID e.g. "2401.12345v1" → "2401.12345"
        short_id = raw_id.split("/abs/")[-1].split("v")[0]

        title = entry.find("atom:title", NS).text.strip().replace("\n", " ")
        abstract = entry.find("atom:summary", NS).text.strip().replace("\n", " ")

        authors = [
            a.find("atom:name", NS).text.strip()
            for a in entry.findall("atom:author", NS)
        ]

        published_str = entry.find("atom:published", NS).text.strip()
        published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))

        categories = [
            tag.get("term")
            for tag in entry.findall("atom:category", NS)
        ]

        papers.append(Paper(
            id=short_id,
            title=title,
            abstract=abstract,
            authors=authors,
            url=f"https://arxiv.org/abs/{short_id}",
            published=published,
            categories=categories,
        ))

    print(f"[fetcher] Got {len(papers)} papers.")
    return papers

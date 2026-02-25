"""
routers/digest.py
POST /digest  { username, topics, categories, max_results, embedding_threshold }
→ runs fetch + filter pipeline, returns list of matched papers as JSON
"""

from fastapi import APIRouter
from pydantic import BaseModel
from fetcher import fetch_recent_papers
from filter import filter_papers, Topic

router = APIRouter()


class DigestRequest(BaseModel):
    username: str
    topics: list[dict]
    categories: list[str] = ["cs.AI", "cs.LG", "cs.CL"]
    max_results: int = 300
    embedding_threshold: float = 0.35


@router.post("/digest")
def run_digest(req: DigestRequest):
    # Convert topic dicts to Topic objects, only enabled ones
    topics = [
        Topic(**t) for t in req.topics
        if t.get("enabled", True)
    ]

    if not topics:
        return {"papers": [], "stats": {"fetched": 0, "matched": 0}}

    # Fetch
    papers = fetch_recent_papers(
        categories=req.categories,
        max_results=req.max_results,
    )

    # Filter (no seen_ids dedup — ephemeral)
    results = filter_papers(
        papers=papers,
        topics=topics,
        embedding_threshold=req.embedding_threshold,
        seen_ids=set(),
    )

    # Serialize
    output = []
    for r in results:
        output.append({
            "id": r.paper.id,
            "title": r.paper.title,
            "abstract": r.paper.abstract,
            "authors": r.paper.authors[:3] + (["et al."] if len(r.paper.authors) > 3 else []),
            "url": f"https://arxiv.org/pdf/{r.paper.id}",
            "published": r.paper.published.isoformat(),
            "topics": r.matched_topics,
            "match_method": r.match_method,
        })

    return {
        "papers": output,
        "stats": {
            "fetched": len(papers),
            "matched": len(results),
        },
    }
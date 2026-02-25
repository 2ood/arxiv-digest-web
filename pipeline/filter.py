"""
filter.py — Two-layer matching:
  1. Synonym/keyword match (fast, rule-based, with stemming)
  2. Semantic embedding similarity (sentence-transformers, local, no API)

A paper passes if EITHER layer fires.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from fetcher import Paper


@dataclass
class Topic:
    id: str
    name: str
    terms: list[str]
    description: str
    enabled: bool = True


@dataclass
class MatchResult:
    paper: Paper
    matched_topics: list[str]          # topic names that matched
    match_method: str                  # "keyword" | "semantic" | "both"
    semantic_scores: dict[str, float] = field(default_factory=dict)


# ─── Layer 1: Keyword / Synonym Matching ────────────────────────────────────

def _normalize(text: str) -> str:
    return text.lower()


def _build_patterns(topics: list[Topic]) -> dict[str, list[re.Pattern]]:
    """Compile regex patterns per topic for fast matching."""
    patterns = {}
    for topic in topics:
        if not topic.enabled:
            continue
        compiled = []
        for term in topic.terms:
            # word-boundary aware, case-insensitive
            # allows partial stem match: "reason" matches "reasoning"
            escaped = re.escape(term.lower())
            # make trailing 'ing/ed/s/er' optional for basic stemming
            pattern = re.compile(
                r'\b' + escaped + r'(?:ing|ed|s|er|ly|tion|ations?)?\b',
                re.IGNORECASE
            )
            compiled.append(pattern)
        patterns[topic.id] = compiled
    return patterns


def keyword_match(
    papers: list[Paper],
    topics: list[Topic],
) -> dict[str, list[str]]:
    """
    Returns dict: paper_id → list of matched topic names.
    Matches against title + abstract.
    """
    patterns = _build_patterns(topics)
    topic_map = {t.id: t for t in topics}
    results: dict[str, list[str]] = {}

    for paper in papers:
        haystack = f"{paper.title} {paper.abstract}".lower()
        matched = []
        for topic_id, compiled_patterns in patterns.items():
            for pat in compiled_patterns:
                if pat.search(haystack):
                    matched.append(topic_map[topic_id].name)
                    break  # one match per topic is enough
        if matched:
            results[paper.id] = matched

    return results


# ─── Layer 2: Semantic Embedding Matching ───────────────────────────────────

def semantic_match(
    papers: list[Paper],
    topics: list[Topic],
    threshold: float = 0.35,
    already_matched_ids: Optional[set] = None,
) -> dict[str, dict]:
    """
    Returns dict: paper_id → {topic_name: score} for papers that pass threshold.
    Only runs on papers NOT already matched by keyword layer (efficiency).
    """
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
    except ImportError:
        print("[filter] sentence-transformers not installed, skipping semantic layer.")
        return {}

    already_matched_ids = already_matched_ids or set()
    enabled_topics = [t for t in topics if t.enabled]

    # Only embed papers not already caught by keyword layer
    candidates = [p for p in papers if p.id not in already_matched_ids]
    if not candidates:
        return {}

    print(f"[filter] Running semantic match on {len(candidates)} papers...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    # Embed paper texts
    paper_texts = [f"{p.title}. {p.abstract[:512]}" for p in candidates]
    paper_embeddings = model.encode(paper_texts, batch_size=64, show_progress_bar=False)

    # Embed topic descriptions
    topic_texts = [t.description for t in enabled_topics]
    topic_embeddings = model.encode(topic_texts, show_progress_bar=False)

    # Cosine similarity
    from numpy.linalg import norm
    paper_norms = paper_embeddings / (norm(paper_embeddings, axis=1, keepdims=True) + 1e-9)
    topic_norms = topic_embeddings / (norm(topic_embeddings, axis=1, keepdims=True) + 1e-9)
    similarity = paper_norms @ topic_norms.T  # (n_papers, n_topics)

    results = {}
    for i, paper in enumerate(candidates):
        matched_topics = {}
        for j, topic in enumerate(enabled_topics):
            score = float(similarity[i, j])
            if score >= threshold:
                matched_topics[topic.name] = round(score, 3)
        if matched_topics:
            results[paper.id] = matched_topics

    return results


# ─── Combined Filter ─────────────────────────────────────────────────────────

def filter_papers(
    papers: list[Paper],
    topics: list[Topic],
    embedding_threshold: float = 0.35,
    seen_ids: Optional[set] = None,
) -> list[MatchResult]:
    """
    Main entry point. Returns matched papers with match metadata.
    Deduplicates against seen_ids if provided.
    """
    seen_ids = seen_ids or set()

    # Filter out already-seen papers
    fresh_papers = [p for p in papers if p.id not in seen_ids]
    print(f"[filter] {len(fresh_papers)} fresh papers (excluded {len(papers) - len(fresh_papers)} seen).")

    if not fresh_papers:
        return []

    # Layer 1: keyword
    keyword_results = keyword_match(fresh_papers, topics)
    print(f"[filter] Keyword layer matched {len(keyword_results)} papers.")

    # Layer 2: semantic (only on unmatched)
    semantic_results = semantic_match(
        fresh_papers,
        topics,
        threshold=embedding_threshold,
        already_matched_ids=set(keyword_results.keys()),
    )
    print(f"[filter] Semantic layer matched {len(semantic_results)} additional papers.")

    # Merge
    paper_map = {p.id: p for p in fresh_papers}
    matched_ids = set(keyword_results) | set(semantic_results)

    results = []
    for pid in matched_ids:
        paper = paper_map[pid]
        in_kw = pid in keyword_results
        in_sem = pid in semantic_results

        if in_kw and in_sem:
            method = "both"
            topics_matched = list(set(keyword_results[pid]) | set(semantic_results[pid].keys()))
        elif in_kw:
            method = "keyword"
            topics_matched = keyword_results[pid]
        else:
            method = "semantic"
            topics_matched = list(semantic_results[pid].keys())

        results.append(MatchResult(
            paper=paper,
            matched_topics=topics_matched,
            match_method=method,
            semantic_scores=semantic_results.get(pid, {}),
        ))

    # Sort by publication date desc
    results.sort(key=lambda r: r.paper.published, reverse=True)
    return results

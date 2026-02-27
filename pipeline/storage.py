"""
storage.py — Persists raw fetched papers as JSON files under data/papers/.

One file per date: data/papers/YYYY-MM-DD.json
Format:
  {
    "date": "2026-02-27",
    "fetched_at": "2026-02-27T07:00:12+09:00",
    "papers": [
      {
        "id": "2502.12345",
        "title": "...",
        "abstract": "...",
        "authors": ["A", "B"],
        "url": "https://arxiv.org/abs/2502.12345",
        "published": "2026-02-27T00:00:00+00:00",
        "categories": ["cs.AI", "cs.LG"]
      },
      ...
    ]
  }

Retention: files older than RETENTION_DAYS are deleted on each run.
"""

import json
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

from fetcher import Paper

RETENTION_DAYS = 90
KST = timezone(timedelta(hours=9))


def _papers_dir(root: Path) -> Path:
    d = root / "data" / "papers"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _path_for_date(root: Path, d: date) -> Path:
    return _papers_dir(root) / f"{d.isoformat()}.json"


# ── Serialise / deserialise ───────────────────────────────────────────────────

def _paper_to_dict(p: Paper) -> dict:
    return {
        "id":         p.id,
        "title":      p.title,
        "abstract":   p.abstract,
        "authors":    p.authors,
        "url":        p.url,
        "published":  p.published.isoformat(),
        "categories": p.categories,
    }


def _dict_to_paper(d: dict) -> Paper:
    return Paper(
        id=d["id"],
        title=d["title"],
        abstract=d["abstract"],
        authors=d["authors"],
        url=d["url"],
        published=datetime.fromisoformat(d["published"]),
        categories=d["categories"],
    )


# ── Public API ────────────────────────────────────────────────────────────────

def save_papers(root: Path, d: date, papers: list[Paper]) -> None:
    """Write papers for a given date to disk. Overwrites if already exists."""
    path = _path_for_date(root, d)
    payload = {
        "date":       d.isoformat(),
        "fetched_at": datetime.now(KST).isoformat(),
        "papers":     [_paper_to_dict(p) for p in papers],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[storage] Saved {len(papers)} papers → {path.name}")


def load_papers(root: Path, d: date) -> list[Paper] | None:
    """
    Load papers for a given date from disk.
    Returns None if the file doesn't exist (date not yet fetched).
    """
    path = _path_for_date(root, d)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    papers  = [_dict_to_paper(p) for p in payload["papers"]]
    print(f"[storage] Loaded {len(papers)} papers ← {path.name}")
    return papers


def date_has_data(root: Path, d: date) -> bool:
    return _path_for_date(root, d).exists()


def list_available_dates(root: Path) -> list[date]:
    """Return all dates that have saved JSON files, sorted newest-first."""
    d = _papers_dir(root)
    dates = []
    for f in d.glob("????-??-??.json"):
        try:
            dates.append(date.fromisoformat(f.stem))
        except ValueError:
            pass
    return sorted(dates, reverse=True)


def prune_old_files(root: Path, retention_days: int = RETENTION_DAYS) -> None:
    """Delete JSON files older than retention_days."""
    cutoff = datetime.now(KST).date() - timedelta(days=retention_days)
    pruned = 0
    for f in _papers_dir(root).glob("????-??-??.json"):
        try:
            file_date = date.fromisoformat(f.stem)
        except ValueError:
            continue
        if file_date < cutoff:
            f.unlink()
            pruned += 1
            print(f"[storage] Pruned {f.name} (older than {retention_days} days)")
    if pruned == 0:
        print(f"[storage] No files to prune (retention: {retention_days} days).")
    else:
        print(f"[storage] Pruned {pruned} file(s).")

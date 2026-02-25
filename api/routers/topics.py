"""
routers/topics.py
GET  /topics/{username}  → return user's topics (or defaults)
POST /topics/{username}  → save user's topics
"""

from fastapi import APIRouter
from pydantic import BaseModel
import json, os, urllib.request

router = APIRouter()

KV_URL   = os.environ.get("KV_REST_API_URL", "")
KV_TOKEN = os.environ.get("KV_REST_API_TOKEN", "")

DEFAULT_TOPICS = [
    {
        "id": "artificial-consciousness",
        "name": "Artificial Consciousness",
        "enabled": True,
        "terms": [
            "artificial consciousness", "machine consciousness", "conscious AI",
            "sentience", "phenomenal experience", "qualia", "self-awareness",
            "subjective experience", "integrated information theory", "IIT",
            "global workspace theory", "GWT", "higher-order theory",
            "cognitive architecture", "inner experience", "awareness",
        ],
        "description": "Papers about machine consciousness, subjective experience, and theories of mind applied to AI systems",
    },
    {
        "id": "test-time-learning",
        "name": "Test-Time Learning",
        "enabled": True,
        "terms": [
            "test-time learning", "test-time training", "TTL", "TTT",
            "test-time compute", "inference-time compute", "inference-time scaling",
            "test-time adaptation", "chain of thought", "CoT", "self-consistency",
            "tree of thought", "ToT", "best-of-N", "majority voting",
            "slow thinking", "extended thinking", "reasoning model",
            "Monte Carlo tree search", "MCTS", "search at inference",
        ],
        "description": "Papers about leveraging more computation at inference time to improve model performance",
    },
    {
        "id": "symbolic",
        "name": "Symbolic AI",
        "enabled": True,
        "terms": [
            "symbolic", "neurosymbolic", "neuro-symbolic",
            "symbolic reasoning", "knowledge graph",
            "formal verification", "theorem proving", "automated reasoning",
            "first-order logic", "FOL", "constraint satisfaction",
            "program synthesis", "rule-based", "knowledge representation",
            "ontology", "inductive logic programming", "ILP",
            "symbolic regression", "hybrid reasoning",
        ],
        "description": "Papers combining neural networks with symbolic reasoning, logic, or structured knowledge",
    },
]


def _kv_key(username: str) -> str:
    return f"topics:{username}"


def _kv_get(key: str):
    if not KV_URL or not KV_TOKEN:
        return None
    req = urllib.request.Request(
        f"{KV_URL}/get/{key}",
        headers={"Authorization": f"Bearer {KV_TOKEN}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            raw = data.get("result")
            return json.loads(raw) if raw else None
    except Exception:
        return None


def _kv_set(key: str, value) -> bool:
    if not KV_URL or not KV_TOKEN:
        return False
    payload = json.dumps({"value": json.dumps(value)}).encode()
    req = urllib.request.Request(
        f"{KV_URL}/set/{key}",
        data=payload,
        headers={
            "Authorization": f"Bearer {KV_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            return True
    except Exception:
        return False


@router.get("/topics/{username}")
def get_topics(username: str):
    data = _kv_get(_kv_key(username))
    return data if data is not None else DEFAULT_TOPICS


class TopicList(BaseModel):
    topics: list[dict]


@router.post("/topics/{username}")
def save_topics(username: str, body: TopicList):
    _kv_set(_kv_key(username), body.topics)
    return {"ok": True}

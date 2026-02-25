"""
config_client.py — Reads topics config and seen_ids from Vercel KV (Redis).
Falls back to local config.json if KV env vars are not set (for local dev).
"""

import os
import json
import urllib.request
from pathlib import Path

from filter import Topic


LOCAL_CONFIG_PATH = Path(__file__).parent / "config.json"

# ─── Default config (used if KV is not configured) ───────────────────────────

DEFAULT_CONFIG = {
    "topics": [
        {
            "id": "artificial-consciousness",
            "name": "Artificial Consciousness",
            "enabled": True,
            "terms": [
                "artificial consciousness", "machine consciousness", "conscious AI",
                "sentience", "phenomenal experience", "qualia", "self-awareness",
                "subjective experience", "integrated information theory", "IIT",
                "global workspace theory", "GWT", "higher-order theory",
                "cognitive architecture", "inner experience", "awareness"
            ],
            "description": "Papers about machine consciousness, subjective experience, and theories of mind applied to AI systems"
        },
        {
            "id": "test-time-learning",
            "name": "Test-Time Learning",
            "enabled": True,
            "terms": [
                "test-time learning", "test-time training", "TTL", "TTT",
                "test-time compute", "inference-time compute", "inference-time scaling",
                "test-time adaptation", "test-time augmentation",
                "chain of thought", "CoT", "self-consistency",
                "tree of thought", "ToT", "best-of-N", "majority voting",
                "slow thinking", "extended thinking", "reasoning model",
                "Monte Carlo tree search", "MCTS", "search at inference"
            ],
            "description": "Papers about leveraging more computation at inference time to improve model performance, including reasoning models and search-based methods"
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
                "symbolic regression", "hybrid reasoning"
            ],
            "description": "Papers combining neural networks with symbolic reasoning, logic, or structured knowledge representations"
        }
    ],
    "config": {
        "email_to": "you@example.com",
        "email_from": "digest@yourdomain.com",
        "categories": ["cs.AI", "cs.LG", "cs.CL"],
        "max_results": 300,
        "embedding_threshold": 0.35
    }
}


# ─── Vercel KV (Upstash Redis REST API) ──────────────────────────────────────

def _kv_get(key: str) -> dict | list | None:
    url = os.environ.get("KV_REST_API_URL")
    token = os.environ.get("KV_REST_API_TOKEN")
    if not url or not token:
        return None
    req = urllib.request.Request(
        f"{url}/get/{key}",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            result = data.get("result")
            if result is None:
                return None
            return json.loads(result)
    except Exception as e:
        print(f"[config] KV get({key}) failed: {e}")
        return None


def _kv_set(key: str, value) -> bool:
    url = os.environ.get("KV_REST_API_URL")
    token = os.environ.get("KV_REST_API_TOKEN")
    if not url or not token:
        return False
    payload = json.dumps({"value": json.dumps(value)}).encode()
    req = urllib.request.Request(
        f"{url}/set/{key}",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True
    except Exception as e:
        print(f"[config] KV set({key}) failed: {e}")
        return False


# ─── Public API ───────────────────────────────────────────────────────────────

def load_topics() -> list[Topic]:
    raw = _kv_get("topics")
    if raw is None:
        # Fall back to local config
        if LOCAL_CONFIG_PATH.exists():
            raw = json.loads(LOCAL_CONFIG_PATH.read_text())["topics"]
        else:
            raw = DEFAULT_CONFIG["topics"]
    return [Topic(**t) for t in raw]


def load_config() -> dict:
    raw = _kv_get("config")
    if raw is None:
        if LOCAL_CONFIG_PATH.exists():
            return json.loads(LOCAL_CONFIG_PATH.read_text())["config"]
        return DEFAULT_CONFIG["config"]
    return raw


def load_seen_ids() -> set[str]:
    raw = _kv_get("seen_ids")
    return set(raw) if raw else set()


def save_seen_ids(seen_ids: set[str]) -> None:
    # Keep only the last 2000 IDs to avoid unbounded growth
    trimmed = list(seen_ids)[-2000:]
    _kv_set("seen_ids", trimmed)


def write_local_default_config():
    """Write default config.json for local dev if it doesn't exist."""
    if not LOCAL_CONFIG_PATH.exists():
        LOCAL_CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2))
        print(f"[config] Wrote default config to {LOCAL_CONFIG_PATH}")

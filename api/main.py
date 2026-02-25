"""
FastAPI app — deploys to Railway.
Exposes:
  GET  /topics/{username}
  POST /topics/{username}
  POST /digest
"""

import sys
from pathlib import Path

# Ensure the api/ directory is on sys.path so all modules are importable
# regardless of where uvicorn is launched from.
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import topics, digest

app = FastAPI(title="arXiv Digest API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your Vercel URL in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(topics.router)
app.include_router(digest.router)


@app.get("/health")
def health():
    return {"status": "ok"}

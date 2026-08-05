"""Optional FastAPI wrapper around the same LangGraph pipeline."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import APP_DISCLAIMER
from src.graph import run_pipeline
from src.vectorstore import get_store

app = FastAPI(
    title="Healthcare AI Evidence Assistant",
    description="Milestone 2 prototype API — RAG + LangGraph",
    version="0.1.0",
)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3)


class AskResponse(BaseModel):
    final_answer: str
    confidence: float
    needs_human_review: bool
    citations: list[dict[str, Any]]
    timings: dict[str, float]
    disclaimer: str


@app.get("/health")
def health() -> dict[str, Any]:
    store = get_store()
    return {"status": "ok", "index": store.meta, "disclaimer": APP_DISCLAIMER}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    out = run_pipeline(req.question)
    cites = []
    for i, h in enumerate(out.get("hits") or [], 1):
        cites.append(
            {
                "n": i,
                "doc_id": h.get("doc_id"),
                "title": h.get("title"),
                "url": h.get("url"),
                "organization": h.get("organization"),
                "score": h.get("score"),
                "chunk_preview": (h.get("text") or "")[:240],
            }
        )
    return AskResponse(
        final_answer=out.get("final_answer") or "",
        confidence=float(out.get("confidence") or 0),
        needs_human_review=bool(out.get("needs_human_review")),
        citations=cites,
        timings=out.get("timings") or {},
        disclaimer=APP_DISCLAIMER,
    )

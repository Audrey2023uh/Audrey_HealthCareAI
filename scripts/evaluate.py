"""Lightweight evaluation: latency, chunks, RAG vs plain-LLM note."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import llm_configured
from src.graph import run_pipeline
from src.llm import chat_json_or_text
from src.vectorstore import VectorStore

QUESTIONS = [
    "What statin intensity is recommended for adults with clinical ASCVD?",
    "What A1C target is commonly used for nonpregnant adults with type 2 diabetes?",
    "When should adults be screened for hypertension according to USPSTF?",
]


def citation_accuracy(hits: list, answer: str) -> dict:
    import re

    cited = [int(x) for x in re.findall(r"\[(\d+)\]", answer or "")]
    valid = [c for c in cited if 1 <= c <= len(hits)]
    return {
        "n_citations": len(cited),
        "n_valid": len(valid),
        "citation_precision": (len(valid) / len(cited)) if cited else None,
        "has_any_citation": bool(cited),
    }


def plain_llm_answer(q: str) -> str:
    if not llm_configured():
        return (
            "[No API key] Plain LLM unavailable. Without RAG, a fluent model could invent "
            "guidelines/doses with no source links — this prototype avoids that by retrieving first."
        )
    return chat_json_or_text(
        [
            {
                "role": "system",
                "content": "Answer the clinical question briefly. Do not claim you retrieved documents.",
            },
            {"role": "user", "content": q},
        ]
    )


def main() -> None:
    # Ensure index
    VectorStore().load()

    rows = []
    for q in QUESTIONS:
        t0 = time.perf_counter()
        out = run_pipeline(q)
        wall = time.perf_counter() - t0
        hits = out.get("hits") or []
        ans = out.get("final_answer") or ""
        cite = citation_accuracy(hits, ans)
        plain = plain_llm_answer(q)
        rows.append(
            {
                "question": q,
                "wall_clock_s": round(wall, 4),
                "timings": out.get("timings"),
                "n_chunks": len(hits),
                "confidence": out.get("confidence"),
                "needs_human_review": out.get("needs_human_review"),
                "citation_accuracy": cite,
                "top_doc_ids": [h.get("doc_id") for h in hits[:3]],
                "groundedness_notes": (out.get("verification") or {}).get("notes"),
                "rag_answer_preview": ans[:400],
                "plain_llm_preview": (plain or "")[:400],
                "qualitative": (
                    "RAG answer includes source-linked chunks; plain LLM has no retrieval audit trail."
                ),
            }
        )
        print(f"OK | {wall:.2f}s | chunks={len(hits)} | conf={out.get('confidence')} | {q[:60]}...")

    out_path = ROOT / "outputs" / "eval_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()

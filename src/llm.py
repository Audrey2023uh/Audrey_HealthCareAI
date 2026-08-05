"""LLM helper with extractive fallback when no API key is configured."""
from __future__ import annotations

import json
import re
from typing import Any

from src.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL, llm_configured


SYSTEM_CLINICAL = """You are a clinical evidence assistant for a university research prototype.
Rules:
- Use ONLY the provided retrieved evidence snippets.
- Evidence is pre-ranked by clinical priorities (Priority 1 guidelines highest → Priority 7 MedQuAD lowest). Prefer higher priorities.
- Do not rely on superseded / archived guideline versions when an active version is present.
- Every factual medical claim must include a citation like [1], [2] matching the evidence list.
- If evidence is insufficient, say so clearly and recommend clinician judgment / guideline review.
- Do NOT invent studies, statistics, doses, or guidelines not present in the evidence.
- This is advisory decision support, not a diagnosis or prescription.
- End with a one-line reminder that a licensed clinician makes the final decision.
"""


def chat_json_or_text(messages: list[dict[str, str]], expect_json: bool = False) -> str:
    if not llm_configured():
        return ""
    try:
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
        kwargs: dict[str, Any] = {
            "model": OPENAI_MODEL,
            "messages": messages,
            "temperature": 0.1,
        }
        if expect_json:
            kwargs["response_format"] = {"type": "json_object"}
        resp = client.chat.completions.create(**kwargs)
        return (resp.choices[0].message.content or "").strip()
    except Exception as exc:
        return f"__LLM_ERROR__:{exc}"


def extractive_answer(query: str, hits: list[dict[str, Any]]) -> str:
    if not hits:
        return (
            "Insufficient retrieved evidence to answer this question grounded in the knowledge base. "
            "Please rephrase or consult primary clinical guidelines. "
            "A licensed clinician must make the final decision."
        )
    lines = [
        f"**Evidence-grounded summary for:** {query}",
        "",
        "The following points are taken from retrieved public medical sources:",
        "",
    ]
    for i, h in enumerate(hits, 1):
        snippet = h["text"]
        if len(snippet) > 420:
            snippet = snippet[:420].rsplit(" ", 1)[0] + "..."
        tier = h.get("evidence_tier", "?")
        lines.append(f"{i}. {snippet} [{i}]")
        lines.append(
            f"   Source: {h.get('organization')} — {h.get('title')} "
            f"(Priority {tier}; semantic={h.get('semantic_score', h.get('score', 0)):.3f}; "
            f"rank={h.get('score', 0):.3f})"
        )
        if h.get("superseded"):
            lines.append("   Note: SUPERSEDED guideline version — prefer newer recommendation.")
        lines.append("")
    lines.append(
        "Confidence is limited to retrieved prototype documents. "
        "Verify against the linked primary sources. A licensed clinician makes the final decision."
    )
    return "\n".join(lines)


def format_evidence_block(hits: list[dict[str, Any]]) -> str:
    blocks = []
    for i, h in enumerate(hits, 1):
        blocks.append(
            f"[{i}] Priority {h.get('evidence_tier', '?')} | {h.get('tier_label', '')}\n"
            f"doc_id={h.get('doc_id')} | {h.get('organization')} | {h.get('title')}\n"
            f"URL: {h.get('url')}\n"
            f"status={h.get('status', 'active')} superseded={h.get('superseded', False)}\n"
            f"semantic_score={h.get('semantic_score', 0):.3f} | final_rank_score={h.get('score', 0):.3f}\n"
            f"evidence_level={h.get('evidence_level')} | recommendation_strength={h.get('recommendation_strength')}\n"
            f"Text: {h.get('text')}\n"
        )
    return "\n".join(blocks)

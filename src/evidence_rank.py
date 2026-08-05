"""
Evidence-priority ranking for clinical retrieval.

Sort / prefer sources in this exact order (1 = highest):

1. Clinical Practice Guidelines (USPSTF, ADA, AHA/ACC, NCCN, NICE, WHO, ...)
2. Systematic Reviews / Meta-Analyses
3. Randomized Clinical Trials
4. PubMed / PubMed Central
5. AHRQ
6. MedlinePlus
7. MedQuAD (testing only)

Not semantic-similarity-only. Not “newest wins” over guidelines.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

# ---------------------------------------------------------------------------
# Priority definitions (1 = highest)
# ---------------------------------------------------------------------------
TIER_LABELS = {
    1: "Priority 1 — Clinical Practice Guidelines",
    2: "Priority 2 — Systematic Reviews / Meta-Analyses",
    3: "Priority 3 — Randomized Clinical Trials",
    4: "Priority 4 — PubMed / PubMed Central",
    5: "Priority 5 — AHRQ",
    6: "Priority 6 — MedlinePlus",
    7: "Priority 7 — MedQuAD (testing only)",
}

PRIORITY_ORDER = [
    "Clinical Practice Guidelines (USPSTF, ADA, AHA/ACC, NCCN, NICE, WHO...)",
    "Systematic Reviews / Meta-Analyses",
    "Randomized Clinical Trials",
    "PubMed / PubMed Central",
    "AHRQ",
    "MedlinePlus",
    "MedQuAD (testing only)",
]

# Guideline societies / agencies for Priority 1 (AHRQ is Priority 5 separately)
TIER1_ORGS = {
    "uspstf",
    "ada",
    "american diabetes association",
    "aha",
    "acc",
    "acc/aha",
    "nccn",
    "idsa",
    "kdigo",
    "gold",
    "gina",
    "asco",
    "esc",
    "esmo",
    "cdc clinical",
    "who",
    "nice",
    "multi-society",
}

SOURCE_TYPE_TIER = {
    "clinical_guideline": 1,
    "guideline": 1,
    "systematic_review": 2,
    "meta_analysis": 2,
    "cochrane": 2,
    "rct": 3,
    "clinical_trial": 3,
    "randomized_trial": 3,
    "pubmed": 4,
    "pubmed_style": 4,
    "pmc": 4,
    "ahrq": 5,
    "medlineplus": 6,
    "medquad_sample": 7,
    "medquad": 7,
    "patient_education": 6,
    "fda": 6,
    "nih": 6,
    "cdc": 6,
    "cohort": 4,  # non-RCT literature defaults toward PubMed tier
}

EVIDENCE_LEVEL_SCORE = {
    "guideline": 1.0,
    "systematic_review": 0.92,
    "meta_analysis": 0.92,
    "cochrane": 0.95,
    "rct": 0.8,
    "large_cohort": 0.72,
    "observational": 0.55,
    "narrative_review": 0.5,
    "expert_opinion": 0.35,
    "patient_education": 0.4,
    "unknown": 0.45,
}

REC_STRENGTH_SCORE = {
    "strong": 1.0,
    "moderate": 0.75,
    "weak": 0.5,
    "insufficient": 0.35,
    "consensus": 0.6,
    "educational": 0.4,
    "unknown": 0.5,
}


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def infer_tier(doc: dict[str, Any]) -> int:
    """Map a document to Priority 1–7."""
    if doc.get("evidence_tier") is not None:
        try:
            t = int(doc["evidence_tier"])
            if 1 <= t <= 7:
                return t
        except (TypeError, ValueError):
            pass

    org = _norm(str(doc.get("organization", "")))
    st = _norm(str(doc.get("source_type", "")))

    # Explicit org overrides
    if "medquad" in org or st in {"medquad", "medquad_sample"}:
        return 7
    if "medlineplus" in org or st == "medlineplus":
        return 6
    if "ahrq" in org or st == "ahrq":
        return 5
    if st in {"pubmed", "pubmed_style", "pmc"} or "pubmed" in org or "pmc" in org:
        # RCT-tagged literature still Priority 3
        if st == "rct" or _norm(str(doc.get("evidence_level", ""))) == "rct":
            return 3
        return 4
    if st in {"rct", "clinical_trial", "randomized_trial"} or _norm(str(doc.get("evidence_level", ""))) == "rct":
        return 3
    if st in {"systematic_review", "meta_analysis", "cochrane"} or "cochrane" in org:
        return 2
    if st in SOURCE_TYPE_TIER:
        return SOURCE_TYPE_TIER[st]
    if any(k in org for k in TIER1_ORGS):
        return 1
    return 4


def _year(doc: dict[str, Any]) -> int:
    for key in ("published_year", "year", "updated_year"):
        v = doc.get(key)
        if v is None or v == "":
            continue
        try:
            return int(str(v)[:4])
        except ValueError:
            continue
    return 0


def freshness_score(doc: dict[str, Any], now_year: int | None = None) -> float:
    now_year = now_year or datetime.utcnow().year
    y = _year(doc)
    if y <= 0:
        return 0.4
    age = max(0, now_year - y)
    tier = infer_tier(doc)
    if tier == 1:
        return max(0.35, 1.0 - 0.04 * age)
    if tier == 2:
        return max(0.3, 1.0 - 0.06 * age)
    if tier == 3:
        return max(0.25, 1.0 - 0.07 * age)
    return max(0.2, 1.0 - 0.08 * age)


def authority_score(doc: dict[str, Any]) -> float:
    org = _norm(str(doc.get("organization", "")))
    if any(k in org for k in ("uspstf", "nice", "who", "cochrane")):
        return 1.0
    if any(k in org for k in ("ada", "acc", "aha", "esc", "nccn", "idsa", "kdigo", "asco", "esmo", "gina", "gold")):
        return 0.95
    if "ahrq" in org:
        return 0.85
    if "medlineplus" in org or "nih" in org or "fda" in org:
        return 0.7
    if "pubmed" in org or "pmc" in org:
        return 0.65
    if "medquad" in org:
        return 0.35
    return float(doc.get("source_credibility", 0.55) or 0.55)


def evidence_quality_score(doc: dict[str, Any]) -> float:
    level = _norm(str(doc.get("evidence_level", "unknown")))
    return EVIDENCE_LEVEL_SCORE.get(level, EVIDENCE_LEVEL_SCORE["unknown"])


def recommendation_score(doc: dict[str, Any]) -> float:
    strength = _norm(str(doc.get("recommendation_strength", "unknown")))
    return REC_STRENGTH_SCORE.get(strength, REC_STRENGTH_SCORE["unknown"])


def superseded_penalty(doc: dict[str, Any]) -> float:
    if doc.get("superseded") or doc.get("is_superseded"):
        return 0.15
    status = _norm(str(doc.get("status", "active")))
    if status in {"superseded", "archived", "withdrawn"}:
        return 0.15
    return 1.0


def clinical_relevance_boost(doc: dict[str, Any], query: str) -> float:
    q = _norm(query)
    if not q:
        return 0.5
    stop = {
        "what", "when", "where", "which", "who", "whom", "whose", "why", "how",
        "should", "would", "could", "about", "with", "from", "that", "this",
        "have", "does", "into", "for", "the", "and", "are", "was", "were",
        "type", "used", "commonly", "help", "measures",
    }
    blob = " ".join(
        [
            str(doc.get("title", "")),
            str(doc.get("organization", "")),
            str(doc.get("topic_key", "")),
            str(doc.get("text", ""))[:500],
        ]
    ).lower()
    tokens = [t for t in q.replace("?", " ").split() if len(t) > 3 and t not in stop]
    if not tokens:
        return 0.5
    hits = sum(1 for t in tokens if t in blob)
    return min(1.0, 0.3 + 0.7 * (hits / max(len(tokens), 1)))


def composite_rank_score(
    doc: dict[str, Any],
    semantic_score: float,
    query: str = "",
    now_year: int | None = None,
) -> dict[str, float]:
    """Within-priority quality score (used after hard sort by Priority 1–7)."""
    tier = infer_tier(doc)
    # Map priority 1..7 → 1.0 .. ~0.14
    tier_component = (8 - tier) / 7.0

    sem = max(0.0, float(semantic_score))
    sem_n = min(1.0, sem / 0.35) if sem <= 1.5 else min(1.0, sem)

    auth = authority_score(doc)
    eq = evidence_quality_score(doc)
    rec = recommendation_score(doc)
    fresh = freshness_score(doc, now_year=now_year)
    rel = clinical_relevance_boost(doc, query)
    pen = superseded_penalty(doc)

    raw = (
        0.30 * tier_component
        + 0.14 * auth
        + 0.12 * eq
        + 0.08 * rec
        + 0.10 * fresh
        + 0.14 * rel
        + 0.12 * sem_n
    ) * pen

    if sem_n < 0.08 and rel < 0.55:
        raw *= 0.25

    return {
        "tier": float(tier),
        "tier_component": round(tier_component, 4),
        "authority": round(auth, 4),
        "evidence_quality": round(eq, 4),
        "recommendation": round(rec, 4),
        "freshness": round(fresh, 4),
        "relevance": round(rel, 4),
        "semantic_norm": round(sem_n, 4),
        "superseded_factor": round(pen, 4),
        "final_score": round(raw, 5),
    }


def rerank_hits(
    hits: list[dict[str, Any]],
    query: str,
    top_k: int = 5,
    prefer_guideline_floor: bool = True,
) -> list[dict[str, Any]]:
    """
    Sort answers by Priority 1 → 7 first, then quality within the same priority.
    """
    scored: list[dict[str, Any]] = []
    for h in hits:
        item = dict(h)
        sem = float(item.get("semantic_score") or item.get("score") or 0.0)
        item["semantic_score"] = sem
        tier = infer_tier(item)
        breakdown = composite_rank_score(item, sem, query=query)
        item["evidence_tier"] = tier
        item["priority"] = tier
        item["tier_label"] = TIER_LABELS.get(tier, f"Priority {tier}")
        item["rank_breakdown"] = breakdown
        item["score"] = breakdown["final_score"]
        scored.append(item)

    # HARD sort: Priority number ascending (1 best), then score, then year, then semantic
    scored.sort(
        key=lambda d: (
            int(d.get("evidence_tier") or 99),
            -float(d.get("score") or 0.0),
            -_year(d),
            -float(d.get("semantic_score") or 0.0),
        )
    )

    deduped: list[dict[str, Any]] = []
    seen_docs: set[str] = set()
    for d in scored:
        did = str(d.get("doc_id") or d.get("chunk_id"))
        if did in seen_docs:
            continue
        seen_docs.add(did)
        deduped.append(d)

    if prefer_guideline_floor:
        active_g = [
            d
            for d in deduped
            if int(d.get("evidence_tier") or 99) == 1
            and superseded_penalty(d) > 0.5
            and float((d.get("rank_breakdown") or {}).get("relevance") or 0) >= 0.5
        ]
        if active_g:
            top = deduped[:top_k]
            if not any(int(x.get("evidence_tier") or 99) == 1 for x in top):
                best_g = active_g[0]
                top = [best_g] + [x for x in top if x.get("doc_id") != best_g.get("doc_id")]
                # re-sort by priority after inject
                top.sort(
                    key=lambda d: (
                        int(d.get("evidence_tier") or 99),
                        -float(d.get("score") or 0.0),
                    )
                )
                return top[:top_k]

    return deduped[:top_k]


def annotate_missing_metadata(doc: dict[str, Any]) -> dict[str, Any]:
    out = dict(doc)
    out["evidence_tier"] = infer_tier(out)
    out.setdefault("evidence_level", "unknown")
    out.setdefault("recommendation_strength", "unknown")
    out.setdefault("superseded", False)
    out.setdefault("status", "archived" if out.get("superseded") else "active")
    out.setdefault("source_credibility", authority_score(out))
    return out


def sort_hits_by_priority(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Public helper: stable Priority 1→7 ordering for UI / answers."""
    return sorted(
        hits,
        key=lambda d: (
            int(d.get("evidence_tier") or infer_tier(d)),
            -float(d.get("score") or 0.0),
            -float(d.get("semantic_score") or 0.0),
        ),
    )

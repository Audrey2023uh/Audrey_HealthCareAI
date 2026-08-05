"""LangGraph multi-agent Clinical Decision Support (CDSS) workflow."""
from __future__ import annotations

import json
import re
import time
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from src.cdss import (
    analyze_clinical_risk,
    build_clinical_recommendation,
    detect_evidence_conflicts,
    extract_patient_from_text,
    merge_patient,
)
from src.config import APP_DISCLAIMER, TOP_K, llm_configured
from src.llm import SYSTEM_CLINICAL, chat_json_or_text, extractive_answer, format_evidence_block
from src.vectorstore import get_store


class GraphState(TypedDict, total=False):
    question: str
    patient_input: dict[str, Any]
    patient_assessment: dict[str, Any]
    risk_analysis: dict[str, Any]
    cleaned_query: str
    query_type: str
    hits: list[dict[str, Any]]
    context: str
    draft_answer: str
    verification: dict[str, Any]
    recommendation: dict[str, Any]
    evidence_summary: list[dict[str, Any]]
    final_answer: str
    confidence: float
    needs_human_review: bool
    timings: dict[str, float]
    agent_trace: list[dict[str, Any]]
    ranking_policy: str
    knowledge_update: dict[str, Any]
    run_knowledge_update: bool
    transparency: dict[str, Any]
    error: str


def _trace(state: GraphState, agent: str, detail: str) -> list[dict[str, Any]]:
    tr = list(state.get("agent_trace") or [])
    tr.append({"agent": agent, "detail": detail, "step": agent})
    return tr


def knowledge_update_agent(state: GraphState) -> GraphState:
    t0 = time.perf_counter()
    report: dict[str, Any] = {"skipped": True}
    if state.get("run_knowledge_update"):
        from src.knowledge_update import run_knowledge_update
        from src import vectorstore as vs_mod

        report = run_knowledge_update(rebuild_index=False)
        vs_mod._STORE = None
    timings = dict(state.get("timings") or {})
    timings["knowledge_update_agent_s"] = time.perf_counter() - t0
    detail = "skipped" if report.get("skipped") else f"sources={report.get('n_sources')}"
    return {
        "knowledge_update": report,
        "timings": timings,
        "agent_trace": _trace(state, "KnowledgeUpdateAgent", detail),
    }


def patient_assessment_agent(state: GraphState) -> GraphState:
    """Step 1 — Patient Assessment."""
    t0 = time.perf_counter()
    q = (state.get("question") or "").strip()
    extracted = extract_patient_from_text(q)
    # Form fills blanks; values found in the clinical question win (avoids stale form state).
    patient = merge_patient(state.get("patient_input"), extracted)
    filled = [
        k
        for k in ("age", "sex", "sbp", "dbp", "diabetes", "ldl", "bmi", "smoking", "clinical_ascvd")
        if patient.get(k) not in (None, "", [], "Unknown")
    ]
    timings = dict(state.get("timings") or {})
    timings["patient_assessment_s"] = time.perf_counter() - t0
    return {
        "patient_assessment": patient,
        "timings": timings,
        "agent_trace": _trace(
            state,
            "Step1_PatientAssessment",
            f"fields_filled={len(filled)}:{','.join(filled) or 'none'}",
        ),
    }


def risk_analysis_agent(state: GraphState) -> GraphState:
    """Step 2 — Clinical Risk Analysis."""
    t0 = time.perf_counter()
    patient = state.get("patient_assessment") or {}
    risk = analyze_clinical_risk(patient)
    timings = dict(state.get("timings") or {})
    timings["risk_analysis_s"] = time.perf_counter() - t0
    return {
        "risk_analysis": risk,
        "timings": timings,
        "agent_trace": _trace(
            state,
            "Step2_RiskAnalysis",
            f"ht={risk.get('hypertension_stage')}; obesity={risk.get('obesity_status')}; "
            f"band={risk.get('cv_risk_band_prototype')}; needs={len(risk.get('preventive_care_needs') or [])}",
        ),
    }


def query_agent(state: GraphState) -> GraphState:
    """Build retrieval query from question + patient/risk context."""
    t0 = time.perf_counter()
    q = (state.get("question") or "").strip()
    patient = state.get("patient_assessment") or {}
    risk = state.get("risk_analysis") or {}

    cleaned = re.sub(r"\s+", " ", q)
    qtype = "general"
    low = cleaned.lower()
    if any(k in low for k in ("statin", "cholesterol", "ascvd", "lipid")) or patient.get("clinical_ascvd"):
        qtype = "cardiovascular_prevention"
    elif any(k in low for k in ("diabetes", "a1c", "glucose", "prediabetes")) or patient.get("diabetes") in {
        "type1",
        "type2",
        "prediabetes",
    }:
        qtype = "diabetes"
    elif any(k in low for k in ("blood pressure", "hypertension", "sbp", "dbp")) or risk.get(
        "hypertension_stage", ""
    ).startswith("stage"):
        qtype = "hypertension"
    elif any(k in low for k in ("screen", "prevention", "guideline")):
        qtype = "screening_guidelines"

    context_bits = []
    if patient.get("age"):
        context_bits.append(f"age {patient['age']}")
    if patient.get("diabetes"):
        context_bits.append(f"diabetes {patient['diabetes']}")
    if risk.get("hypertension_stage") not in (None, "unknown"):
        context_bits.append(str(risk.get("hypertension_stage")))
    if patient.get("clinical_ascvd"):
        context_bits.append("clinical ASCVD")
    for need in (risk.get("preventive_care_needs") or [])[:3]:
        context_bits.append(need.replace("_", " "))

    search_q = cleaned
    if context_bits:
        search_q = f"{cleaned} | patient context: {', '.join(context_bits)}"

    if llm_configured() and cleaned:
        rewritten = chat_json_or_text(
            [
                {
                    "role": "system",
                    "content": (
                        "Rewrite into a concise evidence-search query for clinical guidelines. "
                        "Include relevant patient risk context. Plain text only."
                    ),
                },
                {"role": "user", "content": search_q},
            ]
        )
        if rewritten and not rewritten.startswith("__LLM_ERROR__"):
            search_q = rewritten

    timings = dict(state.get("timings") or {})
    timings["query_agent_s"] = time.perf_counter() - t0
    return {
        "cleaned_query": search_q,
        "query_type": qtype,
        "timings": timings,
        "agent_trace": _trace(state, "QueryAgent", f"type={qtype}; query={search_q[:160]}"),
    }


def retrieval_agent(state: GraphState) -> GraphState:
    """Step 3 — Evidence Retrieval (priority hierarchy)."""
    t0 = time.perf_counter()
    store = get_store()
    q = state.get("cleaned_query") or state.get("question") or ""
    hits = store.search(q, top_k=TOP_K, use_tier_rerank=True)
    if hits:
        hits = [
            h
            for h in hits
            if float(h.get("semantic_score") or 0.0) >= 0.04
            or float((h.get("rank_breakdown") or {}).get("relevance") or 0.0) >= 0.6
        ][:TOP_K] or hits[:1]

    # Prefer non-superseded active guideline versions
    active = [h for h in hits if not h.get("superseded")]
    if active:
        hits = active + [h for h in hits if h.get("superseded")]
        hits = hits[:TOP_K]

    context = format_evidence_block(hits)
    tiers = [int(h.get("evidence_tier") or 0) for h in hits]
    top = hits[0] if hits else {}
    timings = dict(state.get("timings") or {})
    timings["retrieval_agent_s"] = time.perf_counter() - t0
    timings["n_chunks"] = float(len(hits))
    return {
        "hits": hits,
        "context": context,
        "ranking_policy": (
            "P1 Guidelines > P2 SR/MA > P3 RCT > P4 PubMed/PMC > P5 AHRQ > P6 MedlinePlus > P7 MedQuAD"
        ),
        "timings": timings,
        "agent_trace": _trace(
            state,
            "Step3_EvidenceRetrieval",
            f"retrieved={len(hits)}; priorities={tiers}; top={top.get('doc_id')}(P{top.get('evidence_tier')})",
        ),
    }


def verification_agent(state: GraphState) -> GraphState:
    """Step 4 — Evidence Verification (+ groundedness)."""
    t0 = time.perf_counter()
    hits = state.get("hits") or []
    conflict_report = detect_evidence_conflicts(hits)

    # Draft for groundedness (extractive or LLM)
    q = state.get("cleaned_query") or state.get("question") or ""
    context = state.get("context") or ""
    if llm_configured():
        draft = chat_json_or_text(
            [
                {"role": "system", "content": SYSTEM_CLINICAL},
                {
                    "role": "user",
                    "content": (
                        f"Clinical question:\n{q}\n\nRetrieved evidence (priority-ranked):\n{context}\n\n"
                        "Summarize key guideline-concordant points with citations [n]. "
                        "Call out any conflicts explicitly."
                    ),
                },
            ]
        )
        if not draft or draft.startswith("__LLM_ERROR__"):
            draft = extractive_answer(q, hits)
    else:
        draft = extractive_answer(q, hits)

    cited = set(int(x) for x in re.findall(r"\[(\d+)\]", draft))
    unsupported_cites = [c for c in cited if c < 1 or c > len(hits)]
    best_tier = min((int(h.get("evidence_tier") or 9) for h in hits), default=9)
    mean_sem = float(sum(float(h.get("semantic_score") or 0.0) for h in hits) / max(len(hits), 1))
    mean_score = float(sum(float(h.get("score") or 0.0) for h in hits) / max(len(hits), 1))
    n_superseded = sum(1 for h in hits if h.get("superseded"))

    confidence = 0.28
    if hits:
        confidence += min(0.22, mean_score * 0.3)
    if best_tier == 1:
        confidence += 0.18
    elif best_tier == 2:
        confidence += 0.12
    elif best_tier == 3:
        confidence += 0.08
    if cited and not unsupported_cites:
        confidence += 0.1
    if conflict_report.get("conflicts"):
        confidence -= 0.08
    if n_superseded:
        confidence -= 0.06
    patient = state.get("patient_assessment") or {}
    filled = sum(
        1
        for k in ("age", "sbp", "diabetes", "ldl", "bmi", "smoking")
        if patient.get(k) not in (None, "", "Unknown")
    )
    if filled >= 4:
        confidence += 0.08
    elif filled <= 1:
        confidence -= 0.05
        conflict_report.setdefault("agreements", [])
    confidence = round(min(max(confidence, 0.05), 0.95), 3)

    notes = []
    if unsupported_cites:
        notes.append(f"Unsupported citation indices: {unsupported_cites}")
    if mean_sem < 0.05 and hits:
        notes.append("Low semantic similarity — verify clinical relevance.")
    if best_tier >= 6:
        notes.append("Top evidence is MedlinePlus/MedQuAD-level; prefer Priority 1 guidelines.")
    if conflict_report.get("conflicts"):
        notes.append(f"{len(conflict_report['conflicts'])} cross-source conflict theme(s) flagged.")
    if filled <= 1:
        notes.append("Limited patient data — recommendations are more generic.")

    needs_review = (
        confidence < 0.55
        or not hits
        or bool(unsupported_cites)
        or best_tier >= 6
        or bool(conflict_report.get("conflicts"))
        or filled <= 1
    )

    verification = {
        **conflict_report,
        "cited_indices": sorted(cited),
        "unsupported_cites": unsupported_cites,
        "mean_rank_score": mean_score,
        "mean_semantic_score": mean_sem,
        "best_evidence_tier": best_tier if hits else None,
        "n_superseded_in_hits": n_superseded,
        "notes": notes,
        "n_hits": len(hits),
        "ranking_policy": state.get("ranking_policy"),
        "patient_fields_filled": filled,
    }

    timings = dict(state.get("timings") or {})
    timings["verification_agent_s"] = time.perf_counter() - t0
    return {
        "draft_answer": draft,
        "verification": verification,
        "confidence": confidence,
        "needs_human_review": needs_review,
        "timings": timings,
        "agent_trace": _trace(
            state,
            "Step4_EvidenceVerification",
            f"conflicts={len(conflict_report.get('conflicts') or [])}; confidence={confidence}",
        ),
    }


def recommendation_agent(state: GraphState) -> GraphState:
    """Steps 5–6 — Clinical Recommendation + Evidence Summary."""
    t0 = time.perf_counter()
    rec = build_clinical_recommendation(
        question=state.get("question") or "",
        patient=state.get("patient_assessment") or {},
        risk=state.get("risk_analysis") or {},
        hits=state.get("hits") or [],
        verification=state.get("verification") or {},
    )
    timings = dict(state.get("timings") or {})
    timings["recommendation_agent_s"] = time.perf_counter() - t0
    return {
        "recommendation": rec,
        "evidence_summary": rec.get("evidence_summary") or [],
        "timings": timings,
        "agent_trace": _trace(
            state,
            "Step5_6_Recommendation_EvidenceSummary",
            f"recs={len(rec.get('evidence_summary') or [])}; cites={len(rec.get('citations') or [])}",
        ),
    }


def transparency_agent(state: GraphState) -> GraphState:
    """Step 7 — Transparency + final clinician-facing answer."""
    t0 = time.perf_counter()
    hits = state.get("hits") or []
    verification = state.get("verification") or {}
    rec = state.get("recommendation") or {}
    confidence = float(state.get("confidence") or 0.0)
    needs_review = bool(state.get("needs_human_review"))

    transparency = {
        "confidence": confidence,
        "needs_human_review": needs_review,
        "sources_consulted": [
            {
                "n": i,
                "organization": h.get("organization"),
                "title": h.get("title"),
                "year": h.get("year"),
                "priority": h.get("evidence_tier"),
                "url": h.get("url"),
            }
            for i, h in enumerate(hits, 1)
        ],
        "evidence_hierarchy": state.get("ranking_policy"),
        "agent_trace": state.get("agent_trace") or [],
        "conflicts": verification.get("conflicts") or [],
        "disclaimer": APP_DISCLAIMER,
    }

    final = (rec.get("narrative") or state.get("draft_answer") or "").strip()
    final += "\n\n### Step 7 — Transparency\n"
    final += f"- **Confidence:** {confidence:.2f}\n"
    final += f"- **Human review recommended:** {needs_review}\n"
    final += f"- **Evidence hierarchy:** {state.get('ranking_policy')}\n"
    final += f"- **Sources consulted:** {len(hits)}\n"
    if needs_review:
        final += (
            "\n**Human review recommended:** incomplete patient data, limited evidence, "
            "or cross-source disagreement. Verify against primary guidelines before clinical use.\n"
        )
    final += f"\n_{APP_DISCLAIMER}_\n"

    timings = dict(state.get("timings") or {})
    timings["transparency_agent_s"] = time.perf_counter() - t0
    timings["total_pipeline_s"] = sum(
        v for k, v in timings.items() if k.endswith("_s") and k != "total_pipeline_s"
    )
    return {
        "transparency": transparency,
        "final_answer": final,
        "timings": timings,
        "agent_trace": _trace(state, "Step7_Transparency", f"confidence={confidence}; review={needs_review}"),
    }


def build_graph():
    g = StateGraph(GraphState)
    g.add_node("knowledge_update_agent", knowledge_update_agent)
    g.add_node("patient_assessment_agent", patient_assessment_agent)
    g.add_node("risk_analysis_agent", risk_analysis_agent)
    g.add_node("query_agent", query_agent)
    g.add_node("retrieval_agent", retrieval_agent)
    g.add_node("verification_agent", verification_agent)
    g.add_node("recommendation_agent", recommendation_agent)
    g.add_node("transparency_agent", transparency_agent)

    g.set_entry_point("knowledge_update_agent")
    g.add_edge("knowledge_update_agent", "patient_assessment_agent")
    g.add_edge("patient_assessment_agent", "risk_analysis_agent")
    g.add_edge("risk_analysis_agent", "query_agent")
    g.add_edge("query_agent", "retrieval_agent")
    g.add_edge("retrieval_agent", "verification_agent")
    g.add_edge("verification_agent", "recommendation_agent")
    g.add_edge("recommendation_agent", "transparency_agent")
    g.add_edge("transparency_agent", END)
    return g.compile()


_APP = None


def get_app():
    global _APP
    if _APP is None:
        _APP = build_graph()
    return _APP


def run_pipeline(
    question: str,
    patient_input: dict[str, Any] | None = None,
    run_knowledge_update: bool = False,
) -> dict[str, Any]:
    app = get_app()
    result = app.invoke(
        {
            "question": question,
            "patient_input": patient_input or {},
            "timings": {},
            "agent_trace": [],
            "run_knowledge_update": run_knowledge_update,
        }
    )
    return dict(result)

"""
Knowledge Update Agent — checks authoritative sources for newer guidance.

Prototype scope:
- Maintains a source registry of official guideline / org pages
- Periodically HTTP-checks URLs (status, optional Last-Modified / ETag)
- Marks local docs superseded when a newer version is registered
- Rebuilds the FAISS index when updates are applied

Full automated scraping of every society guideline PDF is future work;
this agent provides the executable update loop for the Milestone 2 demo.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from src.config import DATA_DIR, INDEX_DIR, ROOT, SEED_KB

REGISTRY_PATH = DATA_DIR / "source_registry.json"
UPDATE_LOG = INDEX_DIR / "knowledge_update_log.json"


DEFAULT_REGISTRY: dict[str, Any] = {
    "checked_at": None,
    "sources": [
        {
            "org": "USPSTF",
            "topic_key": "statin_primary_prevention",
            "title": "Statin Use for Primary Prevention of CVD",
            "url": "https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/statin-use-in-adults-preventive-medication",
            "current_doc_id": "USPSTF-STATIN-2022",
            "evidence_tier": 1,
            "expected_year": 2022,
        },
        {
            "org": "USPSTF",
            "topic_key": "diabetes_screening",
            "title": "Screening for Prediabetes and Type 2 Diabetes",
            "url": "https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/screening-for-prediabetes-and-type-2-diabetes",
            "current_doc_id": "USPSTF-DIABETES-SCREEN",
            "evidence_tier": 1,
            "expected_year": 2021,
        },
        {
            "org": "USPSTF",
            "topic_key": "hypertension_screening",
            "title": "Hypertension Screening in Adults",
            "url": "https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/hypertension-in-adults-screening",
            "current_doc_id": "USPSTF-HTN-SCREEN",
            "evidence_tier": 1,
            "expected_year": 2021,
        },
        {
            "org": "ADA",
            "topic_key": "glycemic_targets",
            "title": "ADA Standards of Care — glycemic targets (public overview)",
            "url": "https://diabetes.org/about-diabetes",
            "current_doc_id": "ADA-A1C-2024",
            "evidence_tier": 1,
            "expected_year": 2024,
        },
        {
            "org": "ACC/AHA",
            "topic_key": "cholesterol_ascvd",
            "title": "Cholesterol / ASCVD statin intensity themes",
            "url": "https://www.heart.org/en/health-topics/cholesterol",
            "current_doc_id": "ACC-AHA-STATIN-ASCVD",
            "evidence_tier": 1,
            "expected_year": 2018,
        },
        {
            "org": "MedlinePlus",
            "topic_key": "htn_patient_edu",
            "title": "High Blood Pressure",
            "url": "https://medlineplus.gov/highbloodpressure.html",
            "current_doc_id": "MEDLINEPLUS-HTN",
            "evidence_tier": 6,
            "expected_year": 2024,
        },
        {
            "org": "AHRQ",
            "topic_key": "shared_decision",
            "title": "Shared Decision Making",
            "url": "https://www.ahrq.gov/sdm/index.html",
            "current_doc_id": "AHRQ-SHARED-DECISION",
            "evidence_tier": 5,
            "expected_year": 2023,
        },
        {
            "org": "PubMed Central",
            "topic_key": "pmc_portal",
            "title": "PMC open-access archive",
            "url": "https://www.ncbi.nlm.nih.gov/pmc/",
            "current_doc_id": "PMC-OPEN-ACCESS-NOTE",
            "evidence_tier": 4,
            "expected_year": 2024,
        },
    ],
}


def ensure_registry() -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not REGISTRY_PATH.exists():
        REGISTRY_PATH.write_text(json.dumps(DEFAULT_REGISTRY, indent=2), encoding="utf-8")
        return json.loads(json.dumps(DEFAULT_REGISTRY))
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def save_registry(reg: dict[str, Any]) -> None:
    REGISTRY_PATH.write_text(json.dumps(reg, indent=2), encoding="utf-8")


def _probe_url(url: str, timeout: float = 12.0) -> dict[str, Any]:
    out: dict[str, Any] = {
        "url": url,
        "ok": False,
        "status_code": None,
        "last_modified": None,
        "etag": None,
        "error": None,
    }
    try:
        resp = requests.head(url, timeout=timeout, allow_redirects=True)
        # Some sites block HEAD — fall back to GET
        if resp.status_code >= 400:
            resp = requests.get(url, timeout=timeout, allow_redirects=True, stream=True)
            resp.close()
        out["status_code"] = resp.status_code
        out["ok"] = 200 <= resp.status_code < 400
        out["last_modified"] = resp.headers.get("Last-Modified")
        out["etag"] = resp.headers.get("ETag")
    except Exception as exc:
        out["error"] = str(exc)
    return out


def run_knowledge_update(rebuild_index: bool = False) -> dict[str, Any]:
    """
    Knowledge Update Agent entrypoint.
    Returns a structured report suitable for UI / agent_trace.
    """
    reg = ensure_registry()
    results = []
    changed = False
    t0 = time.perf_counter()

    for src in reg.get("sources") or []:
        probe = _probe_url(src["url"])
        prev_lm = src.get("last_modified")
        prev_etag = src.get("etag")
        update_flag = False
        if probe.get("ok"):
            if probe.get("last_modified") and probe["last_modified"] != prev_lm:
                update_flag = bool(prev_lm)  # first observation is baseline, not an alert
            if probe.get("etag") and probe["etag"] != prev_etag and prev_etag:
                update_flag = True
            src["last_modified"] = probe.get("last_modified") or prev_lm
            src["etag"] = probe.get("etag") or prev_etag
            src["last_status"] = probe.get("status_code")
            src["reachable"] = True
        else:
            src["reachable"] = False
            src["last_status"] = probe.get("status_code")
            src["last_error"] = probe.get("error")

        src["checked_at"] = datetime.now(timezone.utc).isoformat()
        results.append(
            {
                "org": src.get("org"),
                "topic_key": src.get("topic_key"),
                "doc_id": src.get("current_doc_id"),
                "tier": src.get("evidence_tier"),
                "url": src.get("url"),
                "reachable": src.get("reachable"),
                "possible_remote_change": update_flag,
                "last_modified": src.get("last_modified"),
            }
        )
        if update_flag:
            changed = True

    # Apply local supersession rules from seed metadata
    superseded_applied = _apply_local_supersession()

    reg["checked_at"] = datetime.now(timezone.utc).isoformat()
    save_registry(reg)

    rebuild_meta = None
    if rebuild_index or superseded_applied:
        from src.vectorstore import VectorStore

        rebuild_meta = VectorStore().build_from_seed(force=True)
        changed = True

    report = {
        "agent": "KnowledgeUpdateAgent",
        "checked_at": reg["checked_at"],
        "n_sources": len(results),
        "possible_remote_changes": sum(1 for r in results if r["possible_remote_change"]),
        "unreachable": sum(1 for r in results if not r["reachable"]),
        "local_supersession_applied": superseded_applied,
        "index_rebuilt": rebuild_meta is not None,
        "rebuild_meta": rebuild_meta,
        "elapsed_s": round(time.perf_counter() - t0, 3),
        "sources": results,
        "note": (
            "Prototype checks official URLs and local superseded flags. "
            "Full automatic ingestion of new guideline PDFs is future work."
        ),
    }
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    UPDATE_LOG.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _apply_local_supersession() -> bool:
    """Ensure superseded docs in seed KB are flagged; returns True if file changed."""
    if not SEED_KB.exists():
        return False
    docs = json.loads(SEED_KB.read_text(encoding="utf-8"))
    by_id = {d["doc_id"]: d for d in docs}
    changed = False
    for d in docs:
        newer = d.get("superseded_by")
        if newer and newer in by_id:
            if not d.get("superseded"):
                d["superseded"] = True
                d["status"] = "superseded"
                changed = True
            newer_doc = by_id[newer]
            if newer_doc.get("supersedes") != d["doc_id"]:
                newer_doc["supersedes"] = d["doc_id"]
                newer_doc["status"] = "active"
                changed = True
    if changed:
        SEED_KB.write_text(json.dumps(docs, indent=2), encoding="utf-8")
    return changed

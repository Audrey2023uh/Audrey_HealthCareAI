"""
Clinical Decision Support System (CDSS) helpers.

Supports a 7-step clinician-assist workflow:
1 Patient Assessment → 2 Risk Analysis → 3 Evidence Retrieval →
4 Evidence Verification → 5 Clinical Recommendation →
6 Evidence Summary → 7 Transparency

Advisory only — does not replace clinician judgment.
"""
from __future__ import annotations

import re
from typing import Any


def empty_patient() -> dict[str, Any]:
    return {
        "age": None,
        "sex": None,
        "sbp": None,
        "dbp": None,
        "diabetes": None,
        "ldl": None,
        "bmi": None,
        "smoking": None,
        "clinical_ascvd": None,
        "other_cv_risk_factors": [],
        "notes": [],
        "raw_text": "",
    }


def merge_patient(base: dict[str, Any] | None, override: dict[str, Any] | None) -> dict[str, Any]:
    out = empty_patient()
    out.update(base or {})
    for k, v in (override or {}).items():
        if v is None or v == "" or v == "Unknown":
            continue
        out[k] = v
    return out


def extract_patient_from_text(text: str) -> dict[str, Any]:
    """Heuristic extraction from free-text clinical question / note."""
    p = empty_patient()
    p["raw_text"] = text or ""
    t = (text or "").lower()

    m = re.search(r"\b(\d{1,3})\s*(?:-?\s*year|\s*yo|\s*y/o|\s*years?\s*old)\b", t)
    if m:
        age = int(m.group(1))
        if 1 <= age <= 120:
            p["age"] = age

    if re.search(r"\b(female|woman|women)\b", t) or re.search(r"\b\d{1,3}\s*-?\s*y(?:ear)?(?:s)?(?:\s*old)?\s*f\b", t):
        p["sex"] = "female"
    elif re.search(r"\b(male|man|men)\b", t) or re.search(r"\b\d{1,3}\s*-?\s*y(?:ear)?(?:\s*old)?\s*m\b", t):
        p["sex"] = "male"

    bp = re.search(r"\b(\d{2,3})\s*/\s*(\d{2,3})\b", t)
    if bp:
        p["sbp"], p["dbp"] = int(bp.group(1)), int(bp.group(2))
    else:
        sbp = re.search(r"\bsbp[:\s]*(\d{2,3})\b", t)
        dbp = re.search(r"\bdbp[:\s]*(\d{2,3})\b", t)
        if sbp:
            p["sbp"] = int(sbp.group(1))
        if dbp:
            p["dbp"] = int(dbp.group(1))

    if re.search(r"\b(type\s*1\s*diabetes|t1dm|dm1)\b", t):
        p["diabetes"] = "type1"
    elif re.search(r"\b(type\s*2\s*diabetes|t2dm|diabetes mellitus|diabetic|dm2)\b", t):
        p["diabetes"] = "type2"
    elif re.search(r"\b(prediabetes|impaired\s+glucose)\b", t):
        p["diabetes"] = "prediabetes"
    elif re.search(r"\bno\s+diabetes|non-?diabetic|without\s+diabetes\b", t):
        p["diabetes"] = "none"

    ldl = re.search(r"\bldl[:\s-]*(\d{2,3})\b", t)
    if ldl:
        p["ldl"] = int(ldl.group(1))

    bmi = re.search(r"\bbmi[:\s]*(\d{2}(?:\.\d)?)\b", t)
    if bmi:
        p["bmi"] = float(bmi.group(1))

    if re.search(r"\b(current\s+smoker|smokes|smoking)\b", t):
        p["smoking"] = "current"
    elif re.search(r"\b(former\s+smoker|ex-?smoker|quit\s+smoking)\b", t):
        p["smoking"] = "former"
    elif re.search(r"\b(never\s+smoker|non-?smoker|does\s+not\s+smoke)\b", t):
        p["smoking"] = "never"

    if re.search(r"\b(clinical\s+ascvd|prior\s+mi|myocardial\s+infarction|stroke|cabg|pci|pad)\b", t):
        p["clinical_ascvd"] = True
        p["other_cv_risk_factors"].append("clinical_ASCVD_history")

    for label, pat in [
        ("hypertension", r"\b(hypertension|high\s+blood\s+pressure)\b"),
        ("dyslipidemia", r"\b(dyslipidemia|hyperlipidemia|high\s+cholesterol)\b"),
        ("family_history_cvd", r"\bfamily\s+history\b"),
        ("ckd", r"\b(ckd|chronic\s+kidney)\b"),
    ]:
        if re.search(pat, t) and label not in p["other_cv_risk_factors"]:
            p["other_cv_risk_factors"].append(label)

    return p


def analyze_clinical_risk(patient: dict[str, Any]) -> dict[str, Any]:
    """Step 2 — structured risk analysis from assessed patient fields."""
    risk_factors: list[str] = []
    preventive_needs: list[str] = []

    age = patient.get("age")
    sbp = patient.get("sbp")
    dbp = patient.get("dbp")
    bmi = patient.get("bmi")
    diabetes = patient.get("diabetes")
    ldl = patient.get("ldl")
    smoking = patient.get("smoking")
    ascvd = patient.get("clinical_ascvd")

    # Hypertension stage (ACC/AHA categories)
    ht_stage = "unknown"
    if sbp is not None and dbp is not None:
        if sbp < 120 and dbp < 80:
            ht_stage = "normal"
        elif 120 <= sbp <= 129 and dbp < 80:
            ht_stage = "elevated"
            risk_factors.append("elevated_blood_pressure")
        elif (130 <= sbp <= 139) or (80 <= dbp <= 89):
            ht_stage = "stage_1_hypertension"
            risk_factors.append("stage_1_hypertension")
        elif sbp >= 140 or dbp >= 90:
            ht_stage = "stage_2_hypertension"
            risk_factors.append("stage_2_hypertension")
        preventive_needs.append("blood_pressure_management_and_follow_up")

    # Obesity
    obesity = "unknown"
    if bmi is not None:
        if bmi < 18.5:
            obesity = "underweight"
        elif bmi < 25:
            obesity = "normal"
        elif bmi < 30:
            obesity = "overweight"
            risk_factors.append("overweight")
        else:
            obesity = "obesity"
            risk_factors.append("obesity")
        if bmi >= 25:
            preventive_needs.append("weight_management_counseling")

    # Diabetes-related risk
    diabetes_risk = "unknown"
    if diabetes == "type2":
        diabetes_risk = "established_type2_diabetes"
        risk_factors.append("type2_diabetes")
        preventive_needs.append("glycemic_and_cardiorenal_risk_management")
    elif diabetes == "type1":
        diabetes_risk = "established_type1_diabetes"
        risk_factors.append("type1_diabetes")
        preventive_needs.append("glycemic_and_cardiorenal_risk_management")
    elif diabetes == "prediabetes":
        diabetes_risk = "prediabetes"
        risk_factors.append("prediabetes")
        preventive_needs.append("diabetes_prevention_lifestyle")
    elif diabetes == "none":
        diabetes_risk = "no_known_diabetes"
        if age and age >= 35 and bmi and bmi >= 25:
            preventive_needs.append("consider_diabetes_screening")

    if smoking == "current":
        risk_factors.append("current_smoking")
        preventive_needs.append("tobacco_cessation")
    elif smoking == "former":
        risk_factors.append("former_smoking")

    if ldl is not None and ldl >= 160:
        risk_factors.append("high_ldl")
        preventive_needs.append("lipid_management_discussion")
    elif ldl is not None and ldl >= 130:
        risk_factors.append("borderline_high_ldl")

    if ascvd:
        risk_factors.append("clinical_ASCVD")
        preventive_needs.append("secondary_prevention_including_statin_intensity_review")
    elif age and 40 <= int(age) <= 75 and (
        diabetes in {"type1", "type2", "prediabetes"}
        or "stage_1_hypertension" in risk_factors
        or "stage_2_hypertension" in risk_factors
        or smoking == "current"
        or (ldl is not None and ldl >= 130)
    ):
        preventive_needs.append("primary_prevention_statin_risk_discussion")

    for extra in patient.get("other_cv_risk_factors") or []:
        if extra not in risk_factors:
            risk_factors.append(extra)

    # Simple ordinal CV risk band for prototype (not a validated calculator)
    score = 0
    if age and age >= 55:
        score += 1
    if age and age >= 65:
        score += 1
    score += len([r for r in risk_factors if r not in {"former_smoking"}])
    if score >= 5 or ascvd:
        cv_band = "high"
    elif score >= 3:
        cv_band = "intermediate"
    elif score >= 1:
        cv_band = "borderline_to_low_moderate"
    else:
        cv_band = "low_or_insufficient_data"

    return {
        "cardiovascular_risk_factors": risk_factors,
        "obesity_status": obesity,
        "hypertension_stage": ht_stage,
        "diabetes_related_risk": diabetes_risk,
        "preventive_care_needs": sorted(set(preventive_needs)),
        "cv_risk_band_prototype": cv_band,
        "analysis_notes": [
            "Prototype risk banding is educational and not a validated ASCVD calculator.",
            "Clinician must confirm measurements, history, and apply full guidelines.",
        ],
    }


def detect_evidence_conflicts(hits: list[dict[str, Any]]) -> dict[str, Any]:
    """Step 4 — compare orgs/tiers and flag possible disagreements."""
    conflicts: list[dict[str, Any]] = []
    agreements: list[str] = []

    by_org: dict[str, list[dict[str, Any]]] = {}
    for h in hits:
        org = str(h.get("organization") or "Unknown")
        by_org.setdefault(org, []).append(h)

    texts = [(h.get("organization"), (h.get("text") or "").lower(), h) for h in hits]
    # Heuristic conflict themes
    themes = [
        (
            "statin_intensity",
            [r"high-?intensity statin", r"moderate-?intensity statin"],
            "Statin intensity wording differs across sources; verify secondary vs primary prevention context.",
        ),
        (
            "a1c_target",
            [r"less than 7%", r"< 7%", r"a1c.*?7", r"individualized"],
            "Glycemic target language may differ (fixed vs individualized); reconcile with ADA patient factors.",
        ),
        (
            "bp_threshold",
            [r"130/80", r"140/90", r"stage 1", r"stage 2"],
            "Blood-pressure category/threshold language differs; confirm ACC/AHA vs other frameworks.",
        ),
        (
            "screening_age",
            [r"35 to 70", r"40 to 75", r"18 years", r"age"],
            "Screening age windows differ by condition/guideline; do not mix diabetes vs hypertension ages.",
        ),
    ]

    for theme, patterns, message in themes:
        matched_orgs = []
        for org, text, h in texts:
            if any(re.search(p, text) for p in patterns):
                matched_orgs.append({"organization": org, "doc_id": h.get("doc_id"), "tier": h.get("evidence_tier")})
        orgs = {m["organization"] for m in matched_orgs}
        if len(orgs) >= 2:
            # Only call conflict if opposing cues present
            joined = " ".join(t for _, t, _ in texts)
            opposing = False
            if theme == "statin_intensity" and (
                re.search(r"high-?intensity", joined) and re.search(r"moderate-?intensity|individualized", joined)
            ):
                opposing = True
            if theme == "bp_threshold" and (
                ("130" in joined or "stage 1" in joined) and ("140" in joined or "stage 2" in joined)
            ):
                opposing = True
            if theme == "a1c_target" and ("individualized" in joined) and re.search(r"7\s*%|< 7", joined):
                opposing = False  # complementary, not conflict
                agreements.append("A1C sources emphasize individualized targets near <7% when safe.")
            if theme == "screening_age" and ("35 to 70" in joined) and ("18 years" in joined):
                opposing = True
            if opposing:
                conflicts.append(
                    {
                        "theme": theme,
                        "message": message,
                        "sources_involved": matched_orgs,
                    }
                )

    if not conflicts:
        agreements.append("No strong cross-source recommendation conflicts detected by prototype heuristics.")

    # Prefer active guidelines over superseded
    superseded = [h for h in hits if h.get("superseded")]
    if superseded:
        conflicts.append(
            {
                "theme": "superseded_guideline",
                "message": "One or more superseded guideline versions were retrieved; prefer the active version.",
                "sources_involved": [
                    {"organization": h.get("organization"), "doc_id": h.get("doc_id"), "tier": h.get("evidence_tier")}
                    for h in superseded
                ],
            }
        )

    return {
        "conflicts": conflicts,
        "agreements": agreements,
        "organizations_consulted": sorted(by_org.keys()),
        "n_sources": len(hits),
    }


def _cite_map(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for i, h in enumerate(hits, 1):
        out.append(
            {
                "n": i,
                "guideline_name": h.get("title"),
                "organization": h.get("organization"),
                "publication_year": h.get("published_year") or h.get("year"),
                "evidence_level": h.get("evidence_level"),
                "evidence_tier": h.get("evidence_tier"),
                "citation": f"[{i}] {h.get('organization')} — {h.get('title')} ({h.get('year')}) {h.get('url')}",
                "url": h.get("url"),
                "doc_id": h.get("doc_id"),
                "status": h.get("status"),
            }
        )
    return out


def build_clinical_recommendation(
    question: str,
    patient: dict[str, Any],
    risk: dict[str, Any],
    hits: list[dict[str, Any]],
    verification: dict[str, Any],
) -> dict[str, Any]:
    """Steps 5–6 — structured recommendations + evidence summary rows."""
    cites = _cite_map(hits)
    factors = risk.get("cardiovascular_risk_factors") or []
    needs = risk.get("preventive_care_needs") or []
    ht = risk.get("hypertension_stage")
    obesity = risk.get("obesity_status")
    diabetes_risk = risk.get("diabetes_related_risk")

    lifestyle: list[dict[str, Any]] = []
    medication: list[dict[str, Any]] = []
    screening: list[dict[str, Any]] = []
    follow_up: list[dict[str, Any]] = []
    preventive: list[dict[str, Any]] = []

    def attach(rec_list: list, text: str, prefer_tiers: set[int] | None = None) -> None:
        prefer_tiers = prefer_tiers or {1, 2, 3}
        linked = [c for c in cites if int(c.get("evidence_tier") or 99) in prefer_tiers] or cites[:2]
        primary = linked[0] if linked else None
        rec_list.append(
            {
                "recommendation": text,
                "guideline_name": (primary or {}).get("guideline_name"),
                "organization": (primary or {}).get("organization"),
                "publication_year": (primary or {}).get("publication_year"),
                "evidence_level": (primary or {}).get("evidence_level"),
                "citation": (primary or {}).get("citation"),
                "supporting_citations": [c["n"] for c in linked[:3]],
            }
        )

    # Lifestyle
    if obesity in {"overweight", "obesity"} or "weight_management_counseling" in needs:
        attach(lifestyle, "Counsel on weight management and calorie-appropriate heart-healthy dietary pattern (e.g., DASH/Mediterranean-style themes).", {1, 6})
    if ht in {"elevated", "stage_1_hypertension", "stage_2_hypertension"} or "blood_pressure_management_and_follow_up" in needs:
        attach(lifestyle, "Lifestyle therapy for blood pressure: sodium reduction, physical activity, weight management, limited alcohol.", {1, 6})
    if "tobacco_cessation" in needs:
        attach(lifestyle, "Offer tobacco cessation support and counseling.", {1, 5, 6})
    if not lifestyle:
        attach(lifestyle, "Reinforce foundational cardiovascular lifestyle counseling (diet, activity, sleep, tobacco avoidance).", {1})

    # Medication
    if patient.get("clinical_ascvd") or "clinical_ASCVD" in factors:
        attach(medication, "For clinical ASCVD, review high-intensity statin therapy (or maximally tolerated intensity) per cholesterol guideline themes.", {1, 2})
    if "primary_prevention_statin_risk_discussion" in needs:
        attach(medication, "Discuss statin therapy for primary prevention based on age, risk factors, and estimated CVD risk; use shared decision-making when benefit is intermediate.", {1, 5})
    if ht in {"stage_1_hypertension", "stage_2_hypertension"}:
        attach(medication, "Assess need for antihypertensive medication using BP stage, ASCVD risk, diabetes/CKD context, and full guideline algorithms.", {1, 3})
    if not medication:
        attach(medication, "No automatic medication start from incomplete data — reconcile therapy choices with guideline indications and clinician judgment.", {1})

    # Screening
    if "consider_diabetes_screening" in needs or diabetes_risk in {"prediabetes", "no_known_diabetes"}:
        attach(screening, "Consider screening for prediabetes/type 2 diabetes in at-risk adults per USPSTF/ADA age and risk-factor themes.", {1})
    if ht == "unknown" or "blood_pressure_management_and_follow_up" in needs:
        attach(screening, "Ensure office BP screening and out-of-office confirmation when diagnosing hypertension (USPSTF themes).", {1})
    if not screening:
        attach(screening, "Confirm age-appropriate preventive screening intervals from active guidelines relevant to this patient.", {1})

    # Follow-up
    attach(follow_up, "Schedule follow-up to reassess BP, lipids, glycemic measures, adherence, and adverse effects after any therapy change.", {1})
    if verification.get("conflicts"):
        attach(follow_up, "Reconcile noted cross-source disagreements with the primary specialty guideline before final orders.", {1})

    # Preventive
    for need in needs:
        attach(preventive, f"Address preventive need: {need.replace('_', ' ')}.", {1, 2, 5})
    if not preventive:
        attach(preventive, "Apply shared decision-making for preventive therapies when guidelines endorse individualized choice.", {1, 5})

    evidence_summary = []
    for block_name, block in [
        ("lifestyle", lifestyle),
        ("medication", medication),
        ("screening", screening),
        ("follow_up", follow_up),
        ("preventive", preventive),
    ]:
        for item in block:
            evidence_summary.append({"category": block_name, **item})

    narrative = _format_recommendation_narrative(
        question, patient, risk, lifestyle, medication, screening, follow_up, preventive, verification, cites
    )

    return {
        "lifestyle_recommendations": lifestyle,
        "medication_recommendations": medication,
        "screening_recommendations": screening,
        "follow_up_recommendations": follow_up,
        "preventive_strategies": preventive,
        "evidence_summary": evidence_summary,
        "citations": cites,
        "narrative": narrative,
    }


def _format_recommendation_narrative(
    question: str,
    patient: dict[str, Any],
    risk: dict[str, Any],
    lifestyle: list,
    medication: list,
    screening: list,
    follow_up: list,
    preventive: list,
    verification: dict[str, Any],
    cites: list,
) -> str:
    lines = [
        "## Clinical Decision Support — Structured Recommendation",
        "",
        f"**Clinical question:** {question}",
        "",
        "### Step 1 — Patient Assessment",
        f"- Age: {patient.get('age')}",
        f"- Sex: {patient.get('sex')}",
        f"- Blood pressure: {patient.get('sbp')}/{patient.get('dbp')} mm Hg",
        f"- Diabetes status: {patient.get('diabetes')}",
        f"- LDL: {patient.get('ldl')}",
        f"- BMI: {patient.get('bmi')}",
        f"- Smoking: {patient.get('smoking')}",
        f"- Clinical ASCVD: {patient.get('clinical_ascvd')}",
        f"- Other CV risk factors: {', '.join(patient.get('other_cv_risk_factors') or []) or 'none listed'}",
        "",
        "### Step 2 — Clinical Risk Analysis",
        f"- CV risk factors: {', '.join(risk.get('cardiovascular_risk_factors') or []) or 'insufficient data'}",
        f"- Obesity status: {risk.get('obesity_status')}",
        f"- Hypertension stage: {risk.get('hypertension_stage')}",
        f"- Diabetes-related risk: {risk.get('diabetes_related_risk')}",
        f"- Preventive care needs: {', '.join(risk.get('preventive_care_needs') or []) or 'none flagged'}",
        f"- Prototype CV risk band: {risk.get('cv_risk_band_prototype')}",
        "",
        "### Step 5 — Clinical Recommendations",
        "**Lifestyle**",
    ]
    for x in lifestyle:
        lines.append(f"- {x['recommendation']} { _cite_inline(x) }")
    lines.append("**Medication**")
    for x in medication:
        lines.append(f"- {x['recommendation']} { _cite_inline(x) }")
    lines.append("**Screening**")
    for x in screening:
        lines.append(f"- {x['recommendation']} { _cite_inline(x) }")
    lines.append("**Follow-up**")
    for x in follow_up:
        lines.append(f"- {x['recommendation']} { _cite_inline(x) }")
    lines.append("**Preventive strategies**")
    for x in preventive:
        lines.append(f"- {x['recommendation']} { _cite_inline(x) }")

    lines += ["", "### Step 4 — Evidence Verification"]
    for a in verification.get("agreements") or []:
        lines.append(f"- Agreement note: {a}")
    for c in verification.get("conflicts") or []:
        lines.append(f"- **Conflict:** {c.get('message')}")

    lines += ["", "### Step 6 — Evidence Summary"]
    for c in cites:
        lines.append(
            f"- [{c['n']}] {c.get('guideline_name')} | {c.get('organization')} | "
            f"{c.get('publication_year')} | level={c.get('evidence_level')} | {c.get('url')}"
        )

    lines += [
        "",
        "### Clinician responsibility",
        "This CDSS output supports clinical decision-making and does **not** replace licensed clinician judgment, "
        "full chart review, or direct reading of primary guidelines.",
    ]
    return "\n".join(lines)


def _cite_inline(item: dict[str, Any]) -> str:
    nums = item.get("supporting_citations") or []
    if not nums:
        return ""
    return " " + "".join(f"[{n}]" for n in nums)
